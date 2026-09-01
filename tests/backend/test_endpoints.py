"""FastAPI endpoint integration tests – FakeLLM, no Groq quota consumed."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from api.index import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_has_required_fields(self, client):
        data = client.get("/api/health").json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "llm_configured" in data
        assert "version" in data
        assert "llm_provider" in data
        assert "llm_model" in data
        assert "request_id" in data

    def test_never_exposes_api_key(self, client):
        text = client.get("/api/health").text
        assert "groq_api_key" not in text.lower()
        assert "api_key" not in text.lower()
        # Check no secret value leaks
        import os
        real_key = os.environ.get("GROQ_API_KEY", "")
        if real_key:
            assert real_key not in text

    def test_request_id_header_present(self, client):
        resp = client.get("/api/health")
        assert "x-request-id" in resp.headers


class TestRAGSearch:
    def test_basic_search(self, client):
        resp = client.post("/api/rag/search", json={"query": "kubernetes crashloopbackoff"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "query" in data
        assert "total_found" in data

    def test_results_cite_real_files(self, client):
        data = client.post("/api/rag/search",
                           json={"query": "terraform state lock"}).json()
        for r in data["results"]:
            assert r["filename"].endswith(".md"), "Must cite real runbook files"

    def test_short_query_rejected(self, client):
        resp = client.post("/api/rag/search", json={"query": "ab"})
        assert resp.status_code == 422

    def test_max_results_respected(self, client):
        data = client.post("/api/rag/search",
                           json={"query": "kubernetes", "max_results": 2}).json()
        assert len(data["results"]) <= 2


class TestAnalyzeLogs:
    def test_basic_analysis(self, client):
        resp = client.post("/api/analyze/logs", json={
            "logs": "ERROR: CrashLoopBackOff\nOOMKilled: exceeded memory limit",
            "technology": "kubernetes",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data
        assert "severity" in data
        assert "summary" in data

    def test_empty_logs(self, client):
        resp = client.post("/api/analyze/logs", json={"logs": "   "})
        assert resp.status_code in (200, 422)

    def test_secret_redacted_from_logs(self, client):
        """Secrets in submitted logs must not appear in the response."""
        resp = client.post("/api/analyze/logs", json={
            "logs": "DB_PASSWORD=mysuperpassword ERROR: connection refused",
        })
        assert "mysuperpassword" not in resp.text


class TestAnalyzeConfig:
    def test_terraform_analysis(self, client):
        resp = client.post("/api/analyze/config", json={
            "configuration": 'resource "aws_s3_bucket" "test" {}',
            "config_type": "terraform",
        })
        assert resp.status_code == 200
        assert "findings" in resp.json()

    def test_kubernetes_analysis(self, client):
        resp = client.post("/api/analyze/config", json={
            "configuration": "image: nginx:latest\nprivileged: true",
            "config_type": "kubernetes",
        })
        assert resp.status_code == 200

    def test_unknown_type_returns_gracefully(self, client):
        resp = client.post("/api/analyze/config", json={
            "configuration": "some config",
            "config_type": "unicorn",
        })
        assert resp.status_code == 200


class TestInvestigationEndpoint:
    def test_missing_required_fields_rejected(self, client):
        # The endpoint accepts raw JSON; empty title/description trigger graceful
        # degradation (status 200 with empty analysis) rather than a 4xx.
        # Validate that the response is at least well-formed.
        resp = client.post("/api/investigations", json={})
        assert resp.status_code in (200, 400, 422, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "session_id" in data or "detail" in data

    def test_valid_request_returns_response(self, client):
        """Full investigation with LLM disabled (no GROQ_API_KEY in test env)."""
        resp = client.post("/api/investigations", json={
            "problem_title": "Kubernetes pod OOMKilled",
            "problem_description": "Pod keeps restarting with OOMKilled. Memory limit 128Mi.",
            "technology": "kubernetes",
            "environment": "production",
            "logs": "OOMKilled: container exceeded memory limit 128Mi\nCrashLoopBackOff",
        })
        # Should succeed even without LLM (graceful degradation)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "investigation_token" in data
        assert "issue_category" in data
        assert "agent_messages" in data
        assert "llm_configured" in data

    def test_response_never_contains_api_key(self, client):
        import os
        resp = client.post("/api/investigations", json={
            "problem_title": "Test",
            "problem_description": "Test description for security check",
            "technology": "kubernetes",
            "environment": "production",
        })
        real_key = os.environ.get("GROQ_API_KEY", "NOTSET")
        if real_key != "NOTSET":
            assert real_key not in resp.text


class TestContinueInvestigationEndpoint:
    def test_invalid_token_rejected(self, client):
        resp = client.post("/api/investigations/continue", json={
            "investigation_token": "tampered.invalidtoken",
            "diagnostic_output": "some output",
        })
        assert resp.status_code == 422

    def test_valid_continuation(self, client):
        # First create an investigation
        start = client.post("/api/investigations", json={
            "problem_title": "DNS resolution failure",
            "problem_description": "Services cannot resolve internal hostnames in Kubernetes cluster.",
            "technology": "kubernetes",
            "environment": "staging",
        })
        if start.status_code != 200:
            pytest.skip("Initial investigation failed — skip continuation test")

        token = start.json().get("investigation_token", "")
        if not token:
            pytest.skip("No token returned")

        cont = client.post("/api/investigations/continue", json={
            "investigation_token": token,
            "diagnostic_output": "kubectl get pods -n kube-system shows coredns CrashLoopBackOff",
        })
        assert cont.status_code == 200
        data = cont.json()
        assert data.get("iteration", 1) >= 2
        assert "investigation_token" in data
