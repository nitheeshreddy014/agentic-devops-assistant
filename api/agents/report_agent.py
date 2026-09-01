"""Report Agent – generates the final, comprehensive troubleshooting report."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from api.core.logging_config import get_logger
from api.providers.llm_provider import invoke_with_retry

logger = get_logger(__name__)

AGENT_ROLE = "Technical Report Writer"
AGENT_GOAL = "Generate a comprehensive, evidence-based troubleshooting report with executive summary, ranked causes, diagnostics, recommended fixes, rollback guidance, and citations"
AGENT_BACKSTORY = (
    "You are a senior technical writer embedded in an SRE team. "
    "You produce post-incident reports and live troubleshooting guides "
    "that engineering leads, on-call engineers, and executives can all act on. "
    "Your reports are precise, evidence-backed, and always include rollback instructions."
)
PHASE = "report"

try:
    from crewai import Agent as CrewAIAgent  # type: ignore[import]
    _CREWAI_AVAILABLE = True
except ImportError:
    _CREWAI_AVAILABLE = False


def _msg(status: str, message: str) -> Dict[str, Any]:
    return {"agent_name": AGENT_ROLE, "phase": PHASE, "status": status,
            "message": message, "timestamp": datetime.now(timezone.utc).isoformat()}


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {}


def _get_persona(llm=None):
    if _CREWAI_AVAILABLE:
        try:
            kw: Dict[str, Any] = {"role": AGENT_ROLE, "goal": AGENT_GOAL, "backstory": AGENT_BACKSTORY,
                                   "allow_delegation": False, "verbose": False}
            if llm is not None:
                kw["llm"] = llm
            a = CrewAIAgent(**kw)
            return a.role, a.goal, a.backstory
        except Exception as e:
            logger.debug(f"CrewAI report: {e}")
    return AGENT_ROLE, AGENT_GOAL, AGENT_BACKSTORY


def _build_base_report(state: dict) -> Dict[str, Any]:
    """Build a complete report purely from state data (no LLM)."""
    causes = state.get("probable_causes", [])
    top_cause = causes[0].get("cause", "Unknown") if causes else "Insufficient evidence to determine"

    evidence = []
    for f in state.get("log_findings", [])[:5]:
        if f.get("is_root_indicator"):
            evidence.append(f"[{f.get('level','?')}] {f.get('message','')[:150]}")
    for f in state.get("config_findings", [])[:3]:
        evidence.append(f"[CONFIG-{f.get('finding_type','?').upper()}] {f.get('description','')[:150]}")

    return {
        "title": f"Investigation Report: {state.get('problem_title', 'DevOps Issue')}",
        "severity": state.get("severity", "unknown"),
        "issue_category": state.get("issue_category", "unknown"),
        "investigation_date": datetime.now(timezone.utc).isoformat(),
        "iteration": state.get("iteration", 1),
        "affected_services": state.get("affected_services", []),
        "error_codes": state.get("error_codes", []),
        "executive_summary": (
            f"{state.get('triage_summary', 'Investigation complete.')} "
            f"Most probable cause: {top_cause}. "
            f"{'Note: AI-powered analysis was unavailable — provide detailed logs and configuration to improve accuracy.' if not state.get('llm_was_used') else ''}"
        ).strip(),
        "missing_information": state.get("missing_info", []),
        "diagnostic_plan": state.get("diagnostic_plan", []),
        "evidence_summary": evidence,
        "probable_causes": state.get("probable_causes", []),
        "diagnostic_steps": state.get("diagnostic_steps", []),
        "recommended_fixes": state.get("recommended_fixes", []),
        "runbook_citations": state.get("runbook_citations", []),
        "flagged_items": state.get("flagged_items", []),
        "rollback_guidance": (
            "Before applying any fix: (1) take a snapshot/backup, "
            "(2) document current state, (3) prepare rollback commands, "
            "(4) notify the on-call team, (5) apply in non-production first."
        ),
        "prevention_recommendations": [
            "Add alerting for this failure mode",
            "Document the fix in the team runbook",
            "Schedule a post-incident review within 48 hours",
            "Add automated tests to detect regression",
        ],
        "next_steps": [
            "Run the suggested diagnostic commands to confirm the root cause",
            "Apply the highest-confidence fix in a staging environment first",
            "Monitor for 30 minutes after applying the fix",
            "If resolved, document in the post-incident report",
            "If unresolved, provide the diagnostic output to continue investigation",
        ],
    }


def run(state: dict, llm: Optional[BaseChatModel]) -> dict:
    msgs: List[Dict[str, Any]] = list(state.get("agent_messages", []))
    msgs.append(_msg("running", "Report Agent: compiling final investigation report…"))

    report = _build_base_report(state)

    # Optionally enrich with LLM-generated content
    if llm is not None:
        role, goal, backstory = _get_persona(llm)

        causes_text = "\n".join(
            f"  #{c.get('rank',i+1)} ({c.get('confidence',0):.0%}): {c.get('cause','')}"
            for i, c in enumerate(state.get("probable_causes", [])[:4])
        ) or "  Unknown"

        fixes_text = "\n".join(
            f"  • {f.get('title','?')}: {f.get('description','')[:100]}"
            for f in state.get("recommended_fixes", [])[:3]
        ) or "  No fixes generated"

        system = f"""You are a {role}. Goal: {goal}
Background: {backstory}

Enrich the investigation report. Return ONLY valid JSON:
{{
  "executive_summary": "<3-4 sentences: what failed, impact, most likely cause, action required>",
  "rollback_guidance": "<specific, actionable rollback steps for this scenario>",
  "prevention_recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"],
  "next_steps": ["<next step 1>", "<next step 2>", "<next step 3>"]
}}"""

        human = (
            f"Title: {report['title']}\n"
            f"Severity: {report['severity']} | Category: {report['issue_category']}\n"
            f"Summary: {state.get('triage_summary','')}\n"
            f"Probable causes:\n{causes_text}\n"
            f"Recommended fixes:\n{fixes_text}\n"
            f"Flagged safety items: {len(state.get('flagged_items', []))}\n"
            f"Citations: {', '.join(c.get('filename','') for c in state.get('runbook_citations',[])[:3])}"
        )

        try:
            resp = invoke_with_retry(llm, [SystemMessage(content=system), HumanMessage(content=human)])
            result = _extract_json(resp.content if hasattr(resp, "content") else str(resp))
            if result:
                report.update({k: v for k, v in result.items() if v})
        except Exception as exc:
            logger.warning(f"Report LLM enrichment (non-fatal): {exc}")

    msgs.append(_msg("complete", f"Final report generated — severity: {report['severity']}, "
                     f"{len(report.get('probable_causes',[]))} cause(s), "
                     f"{len(report.get('recommended_fixes',[]))} fix(es)."))

    return {"agent_messages": msgs, "current_phase": "complete", "report": report}
