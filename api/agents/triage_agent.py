"""Triage Agent – classifies DevOps issues and extracts key diagnostic information."""
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

# ── CrewAI specialist role definition ────────────────────────────────────────
AGENT_ROLE = "DevOps Triage Specialist"
AGENT_GOAL = (
    "Classify DevOps issues by technology domain, extract affected services, "
    "error codes, severity, and identify any missing information needed for diagnosis."
)
AGENT_BACKSTORY = (
    "You are a seasoned Site Reliability Engineer with 15+ years of hands-on experience "
    "across AWS, Azure, GCP, Kubernetes, Terraform, Docker, and all major CI/CD platforms. "
    "You have led incident response for Fortune 500 companies and excel at rapidly "
    "identifying the nature, severity, and scope of infrastructure failures from limited information."
)
PHASE = "triage"

try:
    from crewai import Agent as CrewAIAgent  # type: ignore[import]
    _CREWAI_AVAILABLE = True
except ImportError:
    CrewAIAgent = None
    _CREWAI_AVAILABLE = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _agent_msg(status: str, message: str) -> Dict[str, Any]:
    return {
        "agent_name": AGENT_ROLE,
        "phase": PHASE,
        "status": status,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return {}


def _get_persona(llm=None) -> tuple[str, str, str]:
    """Create CrewAI Agent for role definition and return (role, goal, backstory)."""
    if _CREWAI_AVAILABLE:
        try:
            kwargs: Dict[str, Any] = {
                "role": AGENT_ROLE,
                "goal": AGENT_GOAL,
                "backstory": AGENT_BACKSTORY,
                "allow_delegation": False,
                "verbose": False,
            }
            if llm is not None:
                kwargs["llm"] = llm
            agent = CrewAIAgent(**kwargs)
            return agent.role, agent.goal, agent.backstory
        except Exception as exc:
            logger.debug(f"CrewAI triage agent init (non-critical): {exc}")
    return AGENT_ROLE, AGENT_GOAL, AGENT_BACKSTORY


def _keyword_triage(state: dict, reason: str = "") -> dict:
    """Rule-based fallback when LLM is unavailable or blocked."""
    technology   = state.get("technology", "") or ""
    description  = state.get("problem_description", "") or ""
    title        = state.get("problem_title", "") or ""
    combined     = f"{technology} {title} {description}".lower()

    category = "other"
    for cat in ["terraform", "kubernetes", "docker", "jenkins", "github_actions",
                "aws", "azure", "gcp", "database", "ssl_tls", "dns", "linux", "api", "iam"]:
        if cat.replace("_", "") in combined.replace("_", "").replace(" ", ""):
            category = cat
            break

    display_tech = technology if technology and technology.lower() not in ("other", "unknown") else (
        title.split()[0] if title else "the system"
    )

    note = reason if reason else "AI-powered analysis unavailable — LLM could not be reached."
    return {
        "issue_category": category,
        "severity": "medium",
        "affected_services": [technology] if technology and technology.lower() not in ("other", "") else [],
        "error_codes": [],
        "missing_info": [note],
        "triage_summary": f"Issue detected in {display_tech}. {note}",
    }


# ── Main agent function ───────────────────────────────────────────────────────

def run(state: dict, llm: Optional[BaseChatModel]) -> dict:
    """LangGraph node: triage agent."""
    msgs: List[Dict[str, Any]] = list(state.get("agent_messages", []))
    msgs.append(_agent_msg("running", "Triage Agent: classifying issue and extracting key information…"))

    if llm is None:
        fallback = _keyword_triage(state, reason="LLM not configured — set GROQ_API_KEY to enable AI analysis.")
        msgs.append(_agent_msg("skipped", "LLM not configured — using keyword-based triage."))
        return {"agent_messages": msgs, "current_phase": "triage_complete", **fallback}

    role, goal, backstory = _get_persona(llm)

    system = f"""You are a {role}.
Goal: {goal}
Background: {backstory}

Analyse the DevOps problem and return ONLY a valid JSON object — no markdown, no explanation outside JSON.

JSON schema:
{{
  "issue_category": "<terraform|aws|azure|gcp|kubernetes|docker|jenkins|github_actions|gitlab_ci|linux|database|networking|api|iam|ssl_tls|dns|other>",
  "severity": "<critical|high|medium|low>",
  "affected_services": ["<specific services, components, or resources affected>"],
  "error_codes": ["<specific error codes, HTTP status codes, or named exceptions found in logs>"],
  "missing_info": ["<information not provided that would help diagnosis>"],
  "triage_summary": "<2-3 sentence factual summary of what is failing and the likely business impact>"
}}"""

    human = f"""Problem Title: {state.get('problem_title', 'Untitled')}
Description: {(state.get('problem_description') or '')[:2000]}
Primary Technology: {state.get('technology', 'unknown')}
Environment: {state.get('environment', 'unknown')}
Recent Changes: {(state.get('recent_changes') or 'None provided')[:500]}
Log Excerpt (redacted): {(state.get('logs_redacted') or 'None provided')[:800]}
Config Excerpt (redacted): {(state.get('config_redacted') or 'None provided')[:600]}"""

    try:
        resp = invoke_with_retry(llm, [SystemMessage(content=system), HumanMessage(content=human)])
        content = resp.content if hasattr(resp, "content") else str(resp)
        result = _extract_json(content)
        if result and "issue_category" in result:
            msgs.append(_agent_msg(
                "complete",
                f"Triage complete — category: {result.get('issue_category')}, "
                f"severity: {result.get('severity')}",
            ))
            return {"agent_messages": msgs, "current_phase": "triage_complete", **result}
    except Exception as exc:
        err_str = str(exc)
        is_blocked = any(k in err_str.lower() for k in ("permission", "403", "zscaler", "blocked", "firewall", "doctype", "<!doctype"))
        if is_blocked:
            reason = "LLM request blocked by corporate network/firewall (Zscaler). Request access to api.groq.com via IT helpdesk."
        elif "connection" in err_str.lower() or "timeout" in err_str.lower():
            reason = "LLM unreachable — network connection error. Check proxy/firewall settings."
        else:
            reason = f"LLM error: {err_str[:120]}"
        logger.error(f"Triage LLM error: {err_str[:200]}")
        msgs.append(_agent_msg("error", reason))

    fallback = _keyword_triage(state, reason=reason if 'reason' in locals() else "LLM unavailable.")
    msgs.append(_agent_msg("complete", "Triage completed with keyword fallback."))
    return {"agent_messages": msgs, "current_phase": "triage_complete", **fallback}
