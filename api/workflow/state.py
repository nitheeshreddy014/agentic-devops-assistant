"""LangGraph investigation state – the single source of truth across all nodes."""
from __future__ import annotations

from typing import Any, Dict, List

from typing import TypedDict


class InvestigationState(TypedDict, total=False):
    """
    Mutable state threaded through every LangGraph node.
    total=False means all fields are optional — nodes return only updated keys.
    """
    # ── Identity ───────────────────────────────────────────────────────────────
    session_id: str
    request_id: str
    iteration: int           # 1 = initial, 2+ = continuation

    # ── Redacted input ─────────────────────────────────────────────────────────
    problem_title: str
    problem_description: str
    technology: str
    environment: str
    recent_changes: str
    logs_redacted: str
    config_redacted: str

    # ── Phase tracking ─────────────────────────────────────────────────────────
    current_phase: str

    # ── Triage (node 1) ────────────────────────────────────────────────────────
    issue_category: str
    severity: str
    affected_services: List[str]
    error_codes: List[str]
    missing_info: List[str]
    triage_summary: str

    # ── Plan (node 2) ──────────────────────────────────────────────────────────
    diagnostic_plan: List[str]

    # ── Analysis (node 3) ──────────────────────────────────────────────────────
    log_findings: List[Dict[str, Any]]
    config_findings: List[Dict[str, Any]]

    # ── RAG (node 4) ───────────────────────────────────────────────────────────
    runbook_citations: List[Dict[str, Any]]

    # ── Root causes (node 5) ───────────────────────────────────────────────────
    probable_causes: List[Dict[str, Any]]

    # ── Troubleshooting (node 6) ───────────────────────────────────────────────
    diagnostic_steps: List[Dict[str, Any]]
    recommended_fixes: List[Dict[str, Any]]

    # ── Safety review (node 7) ─────────────────────────────────────────────────
    flagged_items: List[str]
    safety_approved: bool

    # ── Agent timeline ─────────────────────────────────────────────────────────
    agent_messages: List[Dict[str, Any]]

    # ── Continuation ───────────────────────────────────────────────────────────
    user_diagnostic_output: str

    # ── Final report (node 8) ──────────────────────────────────────────────────
    report: Dict[str, Any]

    # ── Errors ─────────────────────────────────────────────────────────────────
    errors: List[str]


def make_initial_state(**overrides: Any) -> InvestigationState:
    """Return a fully-populated initial state with safe defaults."""
    base: InvestigationState = {  # type: ignore[assignment]
        "session_id": "",
        "request_id": "",
        "iteration": 1,
        "problem_title": "",
        "problem_description": "",
        "technology": "",
        "environment": "",
        "recent_changes": "",
        "logs_redacted": "",
        "config_redacted": "",
        "current_phase": "start",
        "issue_category": "",
        "severity": "",
        "affected_services": [],
        "error_codes": [],
        "missing_info": [],
        "triage_summary": "",
        "diagnostic_plan": [],
        "log_findings": [],
        "config_findings": [],
        "runbook_citations": [],
        "probable_causes": [],
        "diagnostic_steps": [],
        "recommended_fixes": [],
        "flagged_items": [],
        "safety_approved": False,
        "agent_messages": [],
        "user_diagnostic_output": "",
        "report": {},
        "errors": [],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base
