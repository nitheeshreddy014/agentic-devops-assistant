"""Root Cause Agent – ranks probable root causes with evidence."""
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

AGENT_ROLE = "Root Cause Analysis Expert"
AGENT_GOAL = "Identify and rank the most probable root causes of the DevOps incident, with supporting evidence, contradicting evidence, and confirmation checks"
AGENT_BACKSTORY = (
    "You are a principal SRE who has led post-incident reviews at hyperscale companies. "
    "You apply the scientific method to infrastructure failures — forming hypotheses, "
    "evaluating evidence for and against each, and ranking causes by probability."
)
PHASE = "root_cause"

try:
    from crewai import Agent as CrewAIAgent  # type: ignore[import]
    _CREWAI_AVAILABLE = True
except ImportError:
    CrewAIAgent = None
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
            logger.debug(f"CrewAI root-cause: {e}")
    return AGENT_ROLE, AGENT_GOAL, AGENT_BACKSTORY


# ── keyword → probable-cause map used by heuristic fallback ─────────────────
_CAUSE_MAP = [
    (["oomkilled", "out of memory", "memory limit"],
     "Container/pod exceeded its memory limit and was OOMKilled",
     "Check `kubectl describe pod <name>` for OOMKilled events and review memory requests/limits"),
    (["crashloopbackoff", "crash loop"],
     "Pod is in CrashLoopBackOff — application is repeatedly crashing on start",
     "Run `kubectl logs <pod> --previous` to view the last crash output"),
    (["imagepullbackoff", "errimagepull", "image pull"],
     "Kubernetes cannot pull the container image — wrong tag, missing credentials, or registry unreachable",
     "Verify image name/tag and ensure imagePullSecrets are configured"),
    (["terraform", "plan failed", "apply failed", "provider", "state lock"],
     "Terraform plan/apply failure — likely a provider configuration error, state lock, or resource drift",
     "Run `terraform plan` with `-detailed-exitcode` and check for state lock with `terraform force-unlock`"),
    (["permission denied", "access denied", "unauthorized", "403", "401"],
     "Insufficient permissions or missing IAM/RBAC role for the requested operation",
     "Review IAM policies / RBAC role bindings and confirm the service account has required permissions"),
    (["connection refused", "connection timed out", "no route to host", "network"],
     "Network connectivity failure — service unreachable or firewall/security-group blocking traffic",
     "Check security group rules, network policies, and service endpoints with `curl` or `nc`"),
    (["certificate", "ssl", "tls", "x509", "cert"],
     "TLS/SSL certificate error — expired, self-signed, or hostname mismatch",
     "Run `openssl s_client -connect <host>:443` and check certificate expiry and SANs"),
    (["dns", "nxdomain", "name resolution", "could not resolve"],
     "DNS resolution failure — hostname cannot be resolved",
     "Check DNS configuration with `nslookup` / `dig` and verify service DNS records"),
    (["disk", "no space left", "disk full", "inode"],
     "Disk or inode exhaustion on the host or persistent volume",
     "Run `df -h` and `df -i` to identify full filesystems; check PVC usage"),
    (["timeout", "deadline exceeded", "request timeout"],
     "Request or operation timed out — service overloaded, slow dependency, or misconfigured timeout",
     "Check downstream service latency, increase timeout values, and review resource utilisation"),
    (["docker", "container", "daemon"],
     "Docker/container runtime issue — daemon error or container configuration problem",
     "Run `docker inspect <container>` and check `journalctl -u docker` for daemon errors"),
    (["jenkins", "pipeline", "ci", "build failed"],
     "CI/CD pipeline failure — build script error, missing dependency, or agent issue",
     "Review the failed stage logs and check agent workspace and environment variables"),
    (["database", "sql", "postgres", "mysql", "mongo", "redis"],
     "Database connectivity or query failure",
     "Check DB logs, connection pool exhaustion, and verify credentials and network access"),
]


def _heuristic_causes(state: dict) -> List[Dict[str, Any]]:
    """Rule-based probable causes from log findings + problem context when LLM unavailable."""
    log_findings = state.get("log_findings", [])
    root_indicators = [f for f in log_findings if f.get("is_root_indicator")]
    if not root_indicators:
        root_indicators = log_findings[:3]

    causes = []
    for i, finding in enumerate(root_indicators[:3]):
        causes.append({
            "rank": i + 1,
            "cause": finding.get("implication", finding.get("message", "Unknown error")[:120]),
            "confidence": 0.6 if i == 0 else 0.4,
            "supporting_evidence": [finding.get("message", "")[:200]],
            "contradicting_evidence": [],
            "confirmation_check": "Review the log line and surrounding context",
            "expected_result": "Confirm the error is reproducible and related to the symptom",
        })

    if not causes:
        # Try to derive a meaningful cause from problem context
        combined = " ".join([
            state.get("problem_title", ""),
            state.get("problem_description", ""),
            state.get("technology", ""),
            state.get("triage_summary", ""),
            state.get("issue_category", ""),
        ]).lower()

        matched_cause, matched_check = None, None
        for keywords, cause_text, check_text in _CAUSE_MAP:
            if any(kw in combined for kw in keywords):
                matched_cause = cause_text
                matched_check = check_text
                break

        technology = state.get("technology", "") or "the system"
        issue_cat  = state.get("issue_category", "other")
        description_snippet = (state.get("problem_description") or "")[:200].strip()

        causes.append({
            "rank": 1,
            "cause": matched_cause or f"Undetermined failure in {technology} ({issue_cat})",
            "confidence": 0.35 if matched_cause else 0.2,
            "supporting_evidence": [
                description_snippet or "No detailed description provided — add logs and config for a richer analysis."
            ],
            "contradicting_evidence": [],
            "confirmation_check": matched_check or (
                f"Collect detailed logs, error messages, and configuration for {technology} "
                "then re-submit to get AI-powered root cause analysis"
            ),
            "expected_result": "Specific error codes and stack traces will narrow down the root cause",
        })

    return causes


def run(state: dict, llm: Optional[BaseChatModel]) -> dict:
    msgs: List[Dict[str, Any]] = list(state.get("agent_messages", []))
    msgs.append(_msg("running", "Root Cause Agent: analysing evidence for probable causes…"))

    if llm is None:
        causes = _heuristic_causes(state)
        msgs.append(_msg("complete", f"Identified {len(causes)} probable cause(s) (heuristic)."))
        return {"agent_messages": msgs, "current_phase": "root_cause_complete", "probable_causes": causes}

    role, goal, backstory = _get_persona(llm)

    # Build evidence summary
    log_summary = "\n".join(
        f"  [{f.get('level','?')}] {f.get('message','')[:150]} → {f.get('implication','')[:100]}"
        for f in state.get("log_findings", [])[:12]
    ) or "  No log findings."

    cfg_summary = "\n".join(
        f"  [{f.get('finding_type','?')}] {f.get('description','')[:150]}"
        for f in state.get("config_findings", [])[:6]
    ) or "  No config findings."

    citation_summary = "\n".join(
        f"  {c.get('filename','')}§{c.get('section','')} — {c.get('snippet','')[:120]}"
        for c in state.get("runbook_citations", [])[:5]
    ) or "  No runbook citations."

    user_output = state.get("user_diagnostic_output", "") or "Not provided yet."

    system = f"""You are a {role}. Goal: {goal}
Background: {backstory}

Analyse ALL provided evidence and return ONLY valid JSON — no markdown, no explanation.

JSON schema:
{{
  "probable_causes": [
    {{
      "rank": 1,
      "cause": "<concise cause statement>",
      "confidence": 0.85,
      "supporting_evidence": ["<fact from logs/config/runbook>", ...],
      "contradicting_evidence": ["<evidence against this cause>", ...],
      "confirmation_check": "<read-only command or observation to confirm>",
      "expected_result": "<what you expect to see if this IS the root cause>"
    }}
  ]
}}

Rules:
- List 2-4 causes ranked by probability (highest first)
- Confidence: 0.0-1.0
- Use only evidence present in the input — never fabricate
- Contradicting evidence may be empty []"""

    human = (
        f"Issue: {state.get('issue_category','?')} | Severity: {state.get('severity','?')}\n"
        f"Summary: {state.get('triage_summary','')}\n"
        f"Technology: {state.get('technology','?')} | Env: {state.get('environment','?')}\n"
        f"Iteration: {state.get('iteration',1)}\n\n"
        f"LOG FINDINGS:\n{log_summary}\n\n"
        f"CONFIG FINDINGS:\n{cfg_summary}\n\n"
        f"RUNBOOK CITATIONS:\n{citation_summary}\n\n"
        f"USER DIAGNOSTIC OUTPUT:\n{user_output[:1000]}"
    )

    try:
        resp = invoke_with_retry(llm, [SystemMessage(content=system), HumanMessage(content=human)])
        result = _extract_json(resp.content if hasattr(resp, "content") else str(resp))
        causes = result.get("probable_causes", [])
        if causes and isinstance(causes, list):
            msgs.append(_msg("complete", f"Identified {len(causes)} probable cause(s). Top: {causes[0].get('cause','?')[:80]}"))
            return {"agent_messages": msgs, "current_phase": "root_cause_complete", "probable_causes": causes}
    except Exception as exc:
        logger.error(f"Root cause LLM error: {exc}")
        msgs.append(_msg("error", str(exc)[:100]))

    causes = _heuristic_causes(state)
    msgs.append(_msg("complete", "Root cause analysis complete (heuristic fallback)."))
    return {"agent_messages": msgs, "current_phase": "root_cause_complete", "probable_causes": causes}
