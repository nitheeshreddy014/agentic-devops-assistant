"""Planner Agent – builds an ordered, iterative investigation plan."""
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

AGENT_ROLE = "Investigation Planning Specialist"
AGENT_GOAL = "Build a structured, ordered diagnostic plan that leads the investigation from safe read-only checks to targeted remediation"
AGENT_BACKSTORY = (
    "You are a principal DevOps consultant who designed investigation frameworks used by SRE "
    "teams at major cloud providers. You know exactly which information to gather first to "
    "maximise diagnostic efficiency and minimise time-to-resolution."
)
PHASE = "plan"

try:
    from crewai import Agent as CrewAIAgent  # type: ignore[import]
    _CREWAI_AVAILABLE = True
except ImportError:
    CrewAIAgent = None
    _CREWAI_AVAILABLE = False


def _agent_msg(status: str, message: str) -> Dict[str, Any]:
    return {"agent_name": AGENT_ROLE, "phase": PHASE, "status": status,
            "message": message, "timestamp": datetime.now(timezone.utc).isoformat()}


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
            logger.debug(f"CrewAI planner: {e}")
    return AGENT_ROLE, AGENT_GOAL, AGENT_BACKSTORY


_TEMPLATES: Dict[str, List[str]] = {
    "kubernetes": [
        "1. Check pod status and recent events: kubectl get pods -n <ns> && kubectl describe pod <name> -n <ns>",
        "2. Review current and previous pod logs: kubectl logs <pod> -n <ns> --previous --tail=200",
        "3. Verify node resource availability: kubectl top nodes && kubectl top pods -n <ns>",
        "4. Inspect deployment spec and rollout history: kubectl describe deployment <name> -n <ns>",
        "5. Check ConfigMaps and Secrets configuration: kubectl get configmap,secret -n <ns>",
        "6. Verify image exists and pull credentials: kubectl describe pod <name> | grep -A5 Events",
        "7. Check resource limits and requests in pod spec",
        "8. Review network policies, Services and Ingress configuration",
        "9. Check HPA/KEDA scaling rules if auto-scaling is enabled",
        "10. Compare current spec with last-known-good deployment",
    ],
    "terraform": [
        "1. Validate configuration: terraform validate",
        "2. Generate plan: terraform plan -out=plan.out 2>&1 | head -100",
        "3. List state resources: terraform state list",
        "4. Verify credentials: aws sts get-caller-identity (or equivalent)",
        "5. Check for state lock: terraform state list (error = lock held)",
        "6. Inspect specific resource: terraform state show <resource>",
        "7. Check provider version constraints in required_providers",
        "8. Review backend configuration for connectivity",
        "9. Show current output values: terraform output",
        "10. Check for drift: terraform plan --refresh-only",
    ],
    "docker": [
        "1. List containers and exit codes: docker ps -a",
        "2. View container logs: docker logs <id> --tail=200",
        "3. Inspect container configuration: docker inspect <id>",
        "4. Check resource usage: docker stats --no-stream",
        "5. Review Dockerfile for build-time issues",
        "6. Verify base image availability: docker pull <image>",
        "7. Check volume mounts and file permissions",
        "8. Test container interactively: docker run -it --entrypoint /bin/sh <image>",
        "9. Check Docker daemon logs: journalctl -u docker --since '1h ago' | tail -50",
        "10. Verify network connectivity: docker network inspect <network>",
    ],
    "aws": [
        "1. Verify IAM identity: aws sts get-caller-identity",
        "2. Check CloudWatch logs for errors: aws logs tail <log-group> --since 1h",
        "3. Describe affected resources and their current state",
        "4. Review IAM policies for permission issues",
        "5. Check VPC, security groups and routing tables",
        "6. Inspect load balancer target health",
        "7. Review CloudTrail for recent API changes",
        "8. Check service quotas and limits",
        "9. Review Auto Scaling Group activity",
        "10. Check SNS/SQS queues for backlog",
    ],
}

_DEFAULT = [
    "1. Gather all relevant logs and error messages",
    "2. Identify the exact failure point and timeline",
    "3. Review recent changes that could have caused the issue",
    "4. Check resource availability (CPU, memory, disk, network)",
    "5. Verify configuration files for errors or misconfigurations",
    "6. Test connectivity to dependent services",
    "7. Search runbooks for known solutions",
    "8. Implement fix in non-production environment first",
    "9. Apply fix with rollback plan ready",
    "10. Verify resolution and monitor for recurrence",
]


def run(state: dict, llm: Optional[BaseChatModel]) -> dict:
    msgs: List[Dict[str, Any]] = list(state.get("agent_messages", []))
    msgs.append(_agent_msg("running", "Planner Agent: building investigation plan…"))

    if llm is None:
        plan = _TEMPLATES.get(state.get("issue_category", ""), _DEFAULT)
        msgs.append(_agent_msg("complete", f"Template plan created ({len(plan)} steps)."))
        return {"agent_messages": msgs, "current_phase": "plan_complete", "diagnostic_plan": plan}

    role, goal, backstory = _get_persona(llm)
    system = f"""You are a {role}. Goal: {goal}
Background: {backstory}

Create an ordered investigation plan. Return ONLY valid JSON:
{{"diagnostic_plan": ["Step 1: <action and rationale>", "Step 2: ...", ...]}}
Rules:
- 8-12 steps ordered safest/fastest first
- Each step is specific and actionable
- Include the technology-specific commands where possible
- Do NOT include destructive commands"""

    human = (
        f"Issue: {state.get('issue_category','?')} | Severity: {state.get('severity','?')}\n"
        f"Summary: {state.get('triage_summary','')}\n"
        f"Affected: {', '.join(state.get('affected_services',[]))}\n"
        f"Error codes: {', '.join(state.get('error_codes',[]))}\n"
        f"Missing info: {', '.join(state.get('missing_info',[]))}\n"
        f"Technology: {state.get('technology','?')} | Env: {state.get('environment','?')}\n"
        f"Recent changes: {(state.get('recent_changes') or 'None')[:400]}"
    )

    try:
        resp = invoke_with_retry(llm, [SystemMessage(content=system), HumanMessage(content=human)])
        result = _extract_json(resp.content if hasattr(resp, "content") else str(resp))
        plan = result.get("diagnostic_plan", [])
        if plan and isinstance(plan, list):
            msgs.append(_agent_msg("complete", f"Plan created with {len(plan)} steps."))
            return {"agent_messages": msgs, "current_phase": "plan_complete", "diagnostic_plan": plan}
    except Exception as exc:
        logger.error(f"Planner error: {exc}")
        msgs.append(_agent_msg("error", str(exc)[:100]))

    plan = _TEMPLATES.get(state.get("issue_category", ""), _DEFAULT)
    msgs.append(_agent_msg("complete", "Template plan used as fallback."))
    return {"agent_messages": msgs, "current_phase": "plan_complete", "diagnostic_plan": plan}
