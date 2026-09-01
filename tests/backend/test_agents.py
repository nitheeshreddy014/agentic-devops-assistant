"""Agent tests using FakeLLM – zero API quota consumed."""
from __future__ import annotations
import pytest
from api.agents import (
    triage_agent, planner_agent, log_analysis_agent,
    rag_knowledge_agent, root_cause_agent, troubleshooting_agent,
    safety_reviewer_agent, report_agent,
)


class TestTriageAgent:
    def test_returns_category_with_llm(self, triage_llm, sample_state):
        result = triage_agent.run(sample_state, triage_llm)
        assert result.get("issue_category") == "kubernetes"
        assert result.get("severity") == "high"
        assert "OOMKilled" in result.get("error_codes", [])

    def test_fallback_without_llm(self, sample_state):
        result = triage_agent.run(sample_state, None)
        assert "issue_category" in result
        assert "severity" in result
        assert len(result.get("agent_messages", [])) > 0

    def test_adds_agent_message(self, triage_llm, sample_state):
        result = triage_agent.run(sample_state, triage_llm)
        msgs = result.get("agent_messages", [])
        assert any(m["phase"] == "triage" for m in msgs)

    def test_never_exposes_llm_key(self, triage_llm, sample_state):
        result = triage_agent.run(sample_state, triage_llm)
        result_str = str(result)
        assert "api_key" not in result_str.lower()
        assert "groq_api_key" not in result_str.lower()


class TestPlannerAgent:
    def test_returns_diagnostic_plan(self, planner_llm, sample_state):
        sample_state["issue_category"] = "kubernetes"
        result = planner_agent.run(sample_state, planner_llm)
        plan = result.get("diagnostic_plan", [])
        assert len(plan) >= 1

    def test_template_fallback_without_llm(self, sample_state):
        sample_state["issue_category"] = "kubernetes"
        result = planner_agent.run(sample_state, None)
        assert len(result.get("diagnostic_plan", [])) > 0


class TestLogAnalysisAgent:
    def test_static_analysis_without_llm(self, sample_state):
        result = log_analysis_agent.run(sample_state, None)
        # Static tools should still work
        assert "log_findings" in result
        assert "config_findings" in result

    def test_augments_with_llm(self, fake_llm, sample_state):
        from tests.conftest import FakeLLM
        llm = FakeLLM({
            "additional_log_findings": [{"level": "ERROR", "message": "OOM",
                                         "context": "ctx", "implication": "Memory issue",
                                         "is_root_indicator": True}],
            "additional_config_findings": [],
            "analysis_notes": "OOM confirmed.",
        })
        result = log_analysis_agent.run(sample_state, llm)
        assert "log_findings" in result


class TestRAGKnowledgeAgent:
    def test_searches_runbooks_without_llm(self, sample_state):
        sample_state["issue_category"] = "kubernetes"
        sample_state["error_codes"] = ["CrashLoopBackOff"]
        result = rag_knowledge_agent.run(sample_state, None)
        citations = result.get("runbook_citations", [])
        # May return 0 if query fails, but should not crash
        assert isinstance(citations, list)

    def test_citations_have_real_filenames(self, sample_state):
        sample_state["issue_category"] = "kubernetes"
        sample_state["triage_summary"] = "Pod CrashLoopBackOff OOMKilled"
        result = rag_knowledge_agent.run(sample_state, None)
        for c in result.get("runbook_citations", []):
            assert c["filename"].endswith(".md")


class TestRootCauseAgent:
    def test_returns_ranked_causes(self, root_cause_llm, sample_state):
        sample_state["log_findings"] = [{"level": "ERROR", "message": "OOMKilled",
                                          "context": "", "implication": "OOM", "is_root_indicator": True}]
        result = root_cause_agent.run(sample_state, root_cause_llm)
        causes = result.get("probable_causes", [])
        assert len(causes) >= 1
        assert causes[0].get("rank") == 1
        assert 0.0 <= causes[0].get("confidence", 0) <= 1.0

    def test_heuristic_fallback_without_llm(self, sample_state):
        sample_state["log_findings"] = [{"level": "ERROR", "message": "OOMKilled",
                                          "context": "", "implication": "OOM", "is_root_indicator": True}]
        result = root_cause_agent.run(sample_state, None)
        assert len(result.get("probable_causes", [])) >= 1


class TestTroubleshootingAgent:
    def test_returns_diagnostic_steps(self, troubleshoot_llm, sample_state):
        sample_state["issue_category"] = "kubernetes"
        sample_state["probable_causes"] = [{"rank": 1, "cause": "OOM", "confidence": 0.85,
                                             "supporting_evidence": [], "contradicting_evidence": [],
                                             "confirmation_check": "", "expected_result": ""}]
        result = troubleshooting_agent.run(sample_state, troubleshoot_llm)
        steps = result.get("diagnostic_steps", [])
        assert len(steps) >= 1
        assert "command" in steps[0]
        assert "risk_level" in steps[0]

    def test_checklist_fallback_without_llm(self, sample_state):
        sample_state["issue_category"] = "kubernetes"
        result = troubleshooting_agent.run(sample_state, None)
        assert len(result.get("diagnostic_steps", [])) > 0


class TestSafetyReviewerAgent:
    def test_flags_dangerous_commands(self, sample_state):
        sample_state["diagnostic_steps"] = [{
            "step_number": 1, "purpose": "test", "command": "rm -rf /var",
            "expected_result": "x", "interpretation": "x",
            "risk_level": "low", "requires_approval": False, "is_safe_readonly": True,
        }]
        sample_state["recommended_fixes"] = []
        result = safety_reviewer_agent.run(sample_state, None)
        assert result["flagged_items"]  # dangerous command was flagged

    def test_readonly_steps_not_flagged_as_dangerous(self, sample_state):
        sample_state["diagnostic_steps"] = [{
            "step_number": 1, "purpose": "check pods", "command": "kubectl get pods",
            "expected_result": "pod list", "interpretation": "ok",
            "risk_level": "low", "requires_approval": False, "is_safe_readonly": True,
        }]
        sample_state["recommended_fixes"] = []
        result = safety_reviewer_agent.run(sample_state, None)
        assert result.get("safety_approved") is True


class TestReportAgent:
    def test_generates_report(self, report_llm, sample_state):
        sample_state["issue_category"] = "kubernetes"
        sample_state["severity"] = "high"
        sample_state["probable_causes"] = [{"rank": 1, "cause": "OOM", "confidence": 0.85,
                                             "supporting_evidence": [], "contradicting_evidence": [],
                                             "confirmation_check": "", "expected_result": ""}]
        result = report_agent.run(sample_state, report_llm)
        report = result.get("report", {})
        assert "title" in report
        assert "severity" in report

    def test_report_without_llm(self, sample_state):
        sample_state["issue_category"] = "kubernetes"
        sample_state["severity"] = "high"
        result = report_agent.run(sample_state, None)
        report = result.get("report", {})
        assert "title" in report
        assert report["severity"] == "high"
