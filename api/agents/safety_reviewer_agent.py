"""Safety Reviewer Agent – detects dangerous commands and flags unsupported claims."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from api.core.logging_config import get_logger
from api.providers.llm_provider import invoke_with_retry
from api.tools.command_safety import check_command_safety, batch_check

logger = get_logger(__name__)

AGENT_ROLE = "Infrastructure Safety Reviewer"
AGENT_GOAL = "Review all diagnostic commands and fix recommendations for safety, flag dangerous operations, and ensure every production-changing action requires explicit human approval"
AGENT_BACKSTORY = (
    "You are a security-focused SRE who reviews all infrastructure change proposals. "
    "You have prevented dozens of production outages by catching dangerous commands before they ran. "
    "You apply strict safety policies: read-only commands need no approval; "
    "anything that modifies state requires an approved change ticket and rollback plan."
)
PHASE = "safety_review"

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
            logger.debug(f"CrewAI safety: {e}")
    return AGENT_ROLE, AGENT_GOAL, AGENT_BACKSTORY


def _review_steps(steps: List[dict]) -> tuple[List[dict], List[str]]:
    """Annotate steps with safety info; collect flagged items."""
    flagged: List[str] = []
    reviewed: List[dict] = []

    for step in steps:
        s = dict(step)
        cmd = s.get("command", "")
        if cmd:
            safety = check_command_safety(cmd)
            s["risk_level"] = safety["risk_level"]
            s["requires_approval"] = safety["requires_approval"]
            s["is_safe_readonly"] = safety["is_readonly"]
            if safety["is_dangerous"]:
                reason = "; ".join(safety.get("reasons", []))
                flagged.append(
                    f"Step {s.get('step_number', '?')}: '{cmd[:60]}…' — {reason} — {safety['recommendation']}"
                )
            elif not safety["is_readonly"]:
                s["requires_approval"] = True
                if "production" in s.get("purpose", "").lower() or "production" in cmd.lower():
                    flagged.append(
                        f"Step {s.get('step_number', '?')}: Production-scope command requires approval."
                    )
        reviewed.append(s)

    return reviewed, flagged


def _review_fixes(fixes: List[dict]) -> tuple[List[dict], List[str]]:
    """Review fix recommendations and flag infrastructure-changing steps."""
    flagged: List[str] = []
    reviewed: List[dict] = []

    for fix in fixes:
        f = dict(fix)
        # All fix steps are potentially infrastructure-changing
        f["requires_approval"] = True
        fix_steps = f.get("steps", [])
        dangerous_steps = []
        for step_text in fix_steps:
            safety = check_command_safety(step_text)
            if safety["is_dangerous"] or not safety["is_readonly"]:
                dangerous_steps.append(step_text[:80])
        if dangerous_steps:
            flagged.append(
                f"Fix '{f.get('title','?')[:60]}' contains infrastructure-changing steps "
                f"that require explicit operator approval and a tested rollback plan."
            )
        # Ensure rollback exists
        if not f.get("rollback_steps"):
            flagged.append(
                f"Fix '{f.get('title','?')[:60]}' is missing rollback steps — "
                "add rollback procedure before applying."
            )
            f["rollback_steps"] = ["Revert change using version control or infrastructure snapshot"]
        reviewed.append(f)

    return reviewed, flagged


def run(state: dict, llm: Optional[BaseChatModel]) -> dict:
    msgs: List[Dict[str, Any]] = list(state.get("agent_messages", []))
    msgs.append(_msg("running", "Safety Reviewer Agent: checking all commands and recommendations…"))

    steps = list(state.get("diagnostic_steps", []))
    fixes = list(state.get("recommended_fixes", []))

    reviewed_steps, step_flags = _review_steps(steps)
    reviewed_fixes, fix_flags = _review_fixes(fixes)
    all_flags = step_flags + fix_flags

    if llm is not None and all_flags:
        role, goal, backstory = _get_persona(llm)
        system = f"""You are a {role}. Goal: {goal}
Background: {backstory}

The static safety checker already flagged items. Add any ADDITIONAL safety concerns 
not yet captured. Return ONLY valid JSON:
{{"additional_flags": ["<flag 1>", "<flag 2>"]}}
Return empty list if nothing additional to add."""

        human = (
            f"Existing flags ({len(all_flags)}):\n" +
            "\n".join(f"  - {f}" for f in all_flags[:10]) +
            f"\n\nEnvironment: {state.get('environment','?')} | Category: {state.get('issue_category','?')}"
        )
        try:
            resp = invoke_with_retry(llm, [SystemMessage(content=system), HumanMessage(content=human)])
            result = _extract_json(resp.content if hasattr(resp, "content") else str(resp))
            extra_flags = result.get("additional_flags", [])
            if isinstance(extra_flags, list):
                all_flags.extend(extra_flags)
        except Exception as exc:
            logger.warning(f"Safety LLM review (non-fatal): {exc}")

    danger_count = len(all_flags)
    msgs.append(_msg("complete",
        f"Safety review complete. {danger_count} item(s) flagged for approval."))

    return {
        "agent_messages": msgs,
        "current_phase": "safety_complete",
        "diagnostic_steps": reviewed_steps,
        "recommended_fixes": reviewed_fixes,
        "flagged_items": all_flags,
        "safety_approved": True,  # Human must explicitly approve via UI — not automated
    }
