"""Shared pytest fixtures — FakeLLM never calls any external API or consumes quota."""
from __future__ import annotations
import json
import pytest
from typing import Any


class _Msg:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """Drop-in replacement for ChatGroq. Returns pre-baked JSON. Zero API calls."""
    def __init__(self, response: dict | None = None):
        self._json = json.dumps(response or {})

    def invoke(self, messages: Any, **_) -> _Msg:
        return _Msg(self._json)

    def __call__(self, messages: Any, **_) -> _Msg:
        return self.invoke(messages)


# ── Canned responses for each agent ─────────────────────────────────────────

@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def triage_llm():
    return FakeLLM({
        "issue_category": "kubernetes",
        "severity": "high",
        "affected_services": ["api-server"],
        "error_codes": ["CrashLoopBackOff", "OOMKilled"],
        "missing_info": [],
        "triage_summary": "Pod is crash-looping due to OOMKilled.",
    })


@pytest.fixture
def planner_llm():
    return FakeLLM({"diagnostic_plan": ["Step 1: Check logs", "Step 2: Verify limits"]})


@pytest.fixture
def root_cause_llm():
    return FakeLLM({
        "probable_causes": [{
            "rank": 1, "cause": "Memory limit too low", "confidence": 0.85,
            "supporting_evidence": ["OOMKilled in logs"],
            "contradicting_evidence": [],
            "confirmation_check": "kubectl top pod <name>",
            "expected_result": "Memory at limit",
        }]
    })


@pytest.fixture
def troubleshoot_llm():
    return FakeLLM({
        "diagnostic_steps": [{
            "step_number": 1, "purpose": "Check memory", "command": "kubectl top pod <name>",
            "expected_result": "Memory near limit", "interpretation": "Confirms OOM",
            "risk_level": "low", "requires_approval": False, "is_safe_readonly": True,
        }],
        "recommended_fixes": [{
            "title": "Increase memory limit",
            "description": "Set limit to 512Mi",
            "steps": ["kubectl edit deployment api"],
            "rollback_steps": ["kubectl rollout undo deployment/api"],
            "risk_level": "medium", "requires_approval": True, "estimated_impact": "Pod restart",
        }],
    })


@pytest.fixture
def report_llm():
    return FakeLLM({
        "executive_summary": "Pod is OOMKilled. Increase memory limit.",
        "rollback_guidance": "kubectl rollout undo deployment/api",
        "prevention_recommendations": ["Set memory limits appropriately"],
        "next_steps": ["Apply fix in staging first"],
    })


@pytest.fixture
def sample_logs():
    return (
        "ERROR: CrashLoopBackOff\n"
        "OOMKilled: container exceeded memory limit 128Mi\n"
        "kubectl: pod api-server-abc restarted 5 times\n"
    )


@pytest.fixture
def sample_k8s_yaml():
    return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: default
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: api
          image: my-api:latest
          resources:
            limits:
              memory: 128Mi
              cpu: 100m
"""


@pytest.fixture
def sample_state():
    return {
        "session_id": "test-session", "request_id": "test-request", "iteration": 1,
        "problem_title": "Kubernetes pod OOMKilled",
        "problem_description": "Pod keeps restarting with OOMKilled",
        "technology": "kubernetes", "environment": "production",
        "recent_changes": "Updated memory limits", "current_phase": "start",
        "logs_redacted": "OOMKilled: container exceeded memory limit 128Mi",
        "config_redacted": "resources:\n  limits:\n    memory: 128Mi",
        "issue_category": "", "severity": "", "affected_services": [],
        "error_codes": [], "missing_info": [], "triage_summary": "",
        "diagnostic_plan": [], "log_findings": [], "config_findings": [],
        "runbook_citations": [], "probable_causes": [], "diagnostic_steps": [],
        "recommended_fixes": [], "flagged_items": [], "safety_approved": False,
        "agent_messages": [], "user_diagnostic_output": "", "report": {}, "errors": [],
    }
