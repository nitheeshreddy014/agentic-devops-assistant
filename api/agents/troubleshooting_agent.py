"""Troubleshooting Agent – ordered diagnostic steps and fix recommendations."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from api.core.logging_config import get_logger
from api.providers.llm_provider import invoke_with_retry
from api.tools.checklist import get_checklist
from api.tools.command_safety import check_command_safety

logger = get_logger(__name__)

AGENT_ROLE = "DevOps Troubleshooting Specialist"
AGENT_GOAL = "Provide ordered, safe, read-only diagnostic commands and actionable fix recommendations with rollback guidance"
AGENT_BACKSTORY = (
    "You are a DevOps engineer with 12 years of experience systematically resolving infrastructure failures. "
    "You build step-by-step diagnostic procedures that guide operators from observation to remediation, "
    "always prioritising safety and reversibility."
)
PHASE = "troubleshoot"

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
            logger.debug(f"CrewAI troubleshoot: {e}")
    return AGENT_ROLE, AGENT_GOAL, AGENT_BACKSTORY


def _annotate_safety(step: dict) -> dict:
    """Run command_safety tool on the step's command and annotate."""
    cmd = step.get("command", "")
    if not cmd:
        return step
    safety = check_command_safety(cmd)
    step["risk_level"] = safety.get("risk_level", "medium")
    step["requires_approval"] = safety.get("requires_approval", False)
    step["is_safe_readonly"] = safety.get("is_readonly", False)
    return step


def _checklist_to_steps(checklist: List[dict]) -> List[Dict[str, Any]]:
    steps = []
    for item in checklist:
        step = {
            "step_number": item.get("step", len(steps) + 1),
            "purpose": item.get("purpose", "Diagnostic check"),
            "command": item.get("command", ""),
            "expected_result": "Diagnostic output showing system state",
            "interpretation": "Review output for anomalies",
            "risk_level": item.get("risk", "low"),
            "requires_approval": item.get("risk", "low") in ("high", "critical"),
            "is_safe_readonly": item.get("risk", "low") == "low",
        }
        step = _annotate_safety(step)
        steps.append(step)
    return steps


def run(state: dict, llm: Optional[BaseChatModel]) -> dict:
    msgs: List[Dict[str, Any]] = list(state.get("agent_messages", []))
    msgs.append(_msg("running", "Troubleshooting Agent: generating diagnostic steps and fixes…"))

    category = state.get("issue_category", "other")
    checklist = get_checklist(category)

    if llm is None:
        steps = _checklist_to_steps(checklist)
        msgs.append(_msg("complete", f"Generated {len(steps)} diagnostic steps (checklist template)."))
        return {"agent_messages": msgs, "current_phase": "troubleshoot_complete",
                "diagnostic_steps": steps, "recommended_fixes": []}

    role, goal, backstory = _get_persona(llm)

    causes_summary = "\n".join(
        f"  #{c.get('rank',i+1)} ({c.get('confidence',0):.0%}) {c.get('cause','?')[:150]}"
        for i, c in enumerate(state.get("probable_causes", [])[:4])
    ) or "  No probable causes identified."

    checklist_text = "\n".join(
        f"  {item.get('step','?')}. {item.get('purpose','')} → {item.get('command','')}"
        for item in checklist[:8]
    )

    system = f"""You are a {role}. Goal: {goal}
Background: {backstory}

Generate ONLY valid JSON — no markdown, no explanation.

JSON schema:
{{
  "diagnostic_steps": [
    {{
      "step_number": 1,
      "purpose": "<why run this>",
      "command": "<exact shell/CLI command — placeholder values like <pod-name> are fine>",
      "expected_result": "<what normal output looks like>",
      "interpretation": "<how to read the output to confirm or deny a cause>",
      "risk_level": "low|medium|high|critical",
      "requires_approval": false,
      "is_safe_readonly": true
    }}
  ],
  "recommended_fixes": [
    {{
      "title": "<short fix title>",
      "description": "<what this fixes and why>",
      "steps": ["<step 1>", "<step 2>", ...],
      "rollback_steps": ["<rollback step 1>", ...],
      "risk_level": "low|medium|high|critical",
      "requires_approval": true,
      "estimated_impact": "<service disruption, downtime, resource usage>"
    }}
  ]
}}

Rules:
- 5-8 diagnostic_steps ordered safest/fastest first (all read-only where possible)
- 2-4 recommended_fixes ordered by confidence
- Every infrastructure-changing fix requires_approval=true
- Provide real, working commands (placeholders like <namespace> are acceptable)"""

    human = (
        f"Category: {category} | Severity: {state.get('severity','?')}\n"
        f"Technology: {state.get('technology','?')} | Env: {state.get('environment','?')}\n\n"
        f"Probable Causes:\n{causes_summary}\n\n"
        f"Triage Summary: {state.get('triage_summary','')}\n\n"
        f"Standard Checklist (adapt as needed):\n{checklist_text}\n\n"
        f"User Diagnostic Output So Far: {(state.get('user_diagnostic_output') or 'None yet')[:600]}"
    )

    try:
        resp = invoke_with_retry(llm, [SystemMessage(content=system), HumanMessage(content=human)])
        result = _extract_json(resp.content if hasattr(resp, "content") else str(resp))
        steps = result.get("diagnostic_steps", [])
        fixes = result.get("recommended_fixes", [])

        # Safety-annotate every step command
        steps = [_annotate_safety(s) for s in steps]

        if steps:
            msgs.append(_msg("complete",
                f"Generated {len(steps)} diagnostic step(s) and {len(fixes)} fix recommendation(s)."))
            return {"agent_messages": msgs, "current_phase": "troubleshoot_complete",
                    "diagnostic_steps": steps, "recommended_fixes": fixes}
    except Exception as exc:
        logger.error(f"Troubleshoot LLM error: {exc}")
        msgs.append(_msg("error", str(exc)[:100]))

    steps = _checklist_to_steps(checklist)
    msgs.append(_msg("complete", "Diagnostic steps generated from checklist fallback."))
    return {"agent_messages": msgs, "current_phase": "troubleshoot_complete",
            "diagnostic_steps": steps, "recommended_fixes": []}
