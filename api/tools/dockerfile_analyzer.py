"""MCP-compatible tool: Dockerfile analysis."""
from __future__ import annotations

import re
from typing import Any, Dict, List

_INSTRUCTION_RE = re.compile(r"^\s*(FROM|RUN|COPY|ADD|ENV|EXPOSE|USER|WORKDIR|CMD|ENTRYPOINT|ARG|LABEL|VOLUME|HEALTHCHECK|SHELL|ONBUILD|STOPSIGNAL)\b", re.I)

_FINDINGS: list[tuple[re.Pattern[str], str, str, str]] = [
    (re.compile(r"^FROM\s+\S+:latest", re.I), "warning",
     "Using :latest tag — non-deterministic builds", "Pin the image to a specific digest or version tag."),
    (re.compile(r"^FROM\s+\S+\s+AS\s+", re.I), "info",
     "Multi-stage build detected", "Good practice — reduces final image size."),
    (re.compile(r"^RUN\s+apt-get\s+install\b(?!.*--no-install-recommends)", re.I), "warning",
     "apt-get install without --no-install-recommends", "Add --no-install-recommends to reduce image size."),
    (re.compile(r"^RUN\s+apt-get\s+update\s*&&?\s*apt-get\s+install\b", re.I), "info",
     "apt-get update combined with install", "Good — avoids cache staleness."),
    (re.compile(r"^ADD\s+https?://", re.I), "warning",
     "ADD fetching remote URL — prefer curl/wget in RUN", "Use RUN curl -fsSL <url> -o <dest> for better caching control."),
    (re.compile(r"^ADD\s+\S+\.tar", re.I), "info",
     "ADD auto-extracts archives", "Consider using COPY + RUN tar for explicit control."),
    (re.compile(r"^RUN\s+.*(sudo\s+|chmod\s+777|chmod\s+-R\s+777)", re.I), "error",
     "Insecure permissions or sudo in RUN", "Run as a dedicated non-root user; avoid world-writable permissions."),
    (re.compile(r"^ENV\s+.*(PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL)\s*=", re.I), "error",
     "Possible secret baked into ENV instruction", "Use build-time ARG (never cached in final layer) or inject secrets at runtime via orchestrator."),
    (re.compile(r"^ARG\s+.*(PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL)\s*=", re.I), "warning",
     "Secret passed via ARG — visible in build history", "Use Docker BuildKit --secret or inject at runtime."),
    (re.compile(r"^RUN\s+pip\s+install\b(?!.*--no-cache-dir)", re.I), "warning",
     "pip install without --no-cache-dir", "Add --no-cache-dir to reduce image size."),
    (re.compile(r"^RUN\s+npm\s+install\b(?!.*--production|.*--omit=dev)", re.I), "warning",
     "npm install without --production flag", "Use --production or --omit=dev for production images."),
    (re.compile(r"^COPY\s+\.\s+\.", re.I), "warning",
     "Copying entire build context — may include secrets or large files",
     "Use a .dockerignore file to exclude .git, node_modules, .env, etc."),
    (re.compile(r"^USER\s+(root|0)\b", re.I), "error",
     "Container running as root", "Add USER <non-root-uid> before CMD/ENTRYPOINT."),
    (re.compile(r"^EXPOSE\s+22\b", re.I), "error",
     "Exposing SSH port 22", "Containers should not run sshd; use kubectl exec or cloud console."),
    (re.compile(r"^(HEALTHCHECK|HEALTHCHECK\s+--)", re.I), "info",
     "HEALTHCHECK defined", "Good — enables container health monitoring."),
    (re.compile(r"^RUN\s+.*curl.*\|\s*(ba)?sh", re.I), "error",
     "Piping remote script to shell in RUN", "Download, inspect, then execute separately."),
    (re.compile(r"^RUN\s+wget.*\|\s*(ba)?sh", re.I), "error",
     "Piping wget to shell in RUN", "Download, inspect, then execute separately."),
    (re.compile(r"^RUN\s+.*(&&\s*){3,}", re.I), "warning",
     "Long RUN chain — hard to debug failures", "Consider splitting into separate RUN instructions during development."),
    (re.compile(r"MAINTAINER\s+", re.I), "warning",
     "MAINTAINER instruction is deprecated", "Use LABEL maintainer='...' instead."),
]


def analyze_dockerfile(dockerfile_text: str) -> Dict[str, Any]:
    """
    MCP-compatible stateless tool: analyse Dockerfile content.
    Input is treated as plain text — NEVER executed.
    """
    if not dockerfile_text or not dockerfile_text.strip():
        return {"findings": [], "summary": "No Dockerfile content provided.", "severity": "low"}

    lines = dockerfile_text.splitlines()
    findings: List[Dict[str, Any]] = []
    base_images: List[str] = []
    instructions: Dict[str, int] = {}
    has_user_instruction = False
    has_healthcheck = False
    is_multistage = False
    seen_keys: set[str] = set()

    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Count instructions
        m = _INSTRUCTION_RE.match(line)
        if m:
            instr = m.group(1).upper()
            instructions[instr] = instructions.get(instr, 0) + 1
            if instr == "USER" and not re.search(r"root|^0$", line, re.I):
                has_user_instruction = True
            if instr == "HEALTHCHECK":
                has_healthcheck = True
            if instr == "FROM":
                fm = re.match(r"FROM\s+(\S+)", line, re.I)
                if fm:
                    base_images.append(fm.group(1))
                if re.search(r"\bAS\s+", line, re.I):
                    is_multistage = True

        # Pattern analysis
        for pattern, ftype, desc, rec in _FINDINGS:
            if ftype == "info":
                continue
            if pattern.search(line):
                key = f"{ftype}:{desc}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    findings.append({
                        "finding_type": ftype,
                        "location": f"line {i + 1}: {line[:100]}",
                        "description": desc,
                        "recommendation": rec,
                    })
                break

    # Structural checks
    if instructions.get("USER", 0) == 0:
        findings.append({
            "finding_type": "warning",
            "location": "Dockerfile (global)",
            "description": "No USER instruction — container runs as root by default",
            "recommendation": "Add 'USER nonroot' or a specific UID before CMD/ENTRYPOINT.",
        })

    if not has_healthcheck:
        findings.append({
            "finding_type": "warning",
            "location": "Dockerfile (global)",
            "description": "No HEALTHCHECK instruction",
            "recommendation": "Add HEALTHCHECK to enable health monitoring.",
        })

    if instructions.get("FROM", 0) > 1 and not is_multistage:
        findings.append({
            "finding_type": "warning",
            "location": "Dockerfile (global)",
            "description": "Multiple FROM instructions detected — verify multi-stage build intent",
            "recommendation": "Ensure each FROM stage is intentional.",
        })

    severity = "low"
    if any(f["finding_type"] == "error" for f in findings):
        severity = "high"
    elif any(f["finding_type"] == "warning" for f in findings):
        severity = "medium"

    summary = (
        f"Analysed Dockerfile with {len(lines)} lines. "
        f"Base image(s): {', '.join(base_images) or 'none detected'}. "
        f"Multi-stage: {is_multistage}. "
        f"Found {len(findings)} issue(s). Severity: {severity}."
    )

    return {
        "findings": findings,
        "base_images": base_images,
        "instructions_count": instructions,
        "is_multistage": is_multistage,
        "has_healthcheck": has_healthcheck,
        "has_user_instruction": has_user_instruction,
        "summary": summary,
        "severity": severity,
    }
