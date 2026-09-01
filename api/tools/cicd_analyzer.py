"""MCP-compatible tool: CI/CD pipeline YAML / Jenkinsfile analysis."""
from __future__ import annotations

import re
from typing import Any, Dict, List

try:
    import yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

# ── Detection ─────────────────────────────────────────────────────────────────
def _detect_cicd_type(text: str) -> str:
    if "pipeline {" in text or "Jenkinsfile" in text or "agent {" in text:
        return "jenkins"
    if re.search(r"^on:\s*$|^jobs:\s*$", text, re.M):
        return "github_actions"
    if re.search(r"^stages:\s*$|^\.gitlab-ci\b", text, re.M):
        return "gitlab_ci"
    if re.search(r"^image:\s*\S|^pipelines:", text, re.M):
        return "bitbucket_pipelines"
    return "generic"

# ── Pattern findings ──────────────────────────────────────────────────────────
_PATTERNS: list[tuple[re.Pattern[str], str, str, str, str]] = [
    # GitHub Actions
    (re.compile(r"uses:\s*\S+@v\d", re.I), "info", "github_actions",
     "Action pinned to major version tag — mutable", "Pin to a specific SHA for reproducibility: uses: actions/checkout@abc1234"),
    (re.compile(r"uses:\s*\S+@main|uses:\s*\S+@master", re.I), "error", "github_actions",
     "Action pinned to mutable branch (main/master)", "Pin to a specific commit SHA to prevent supply-chain attacks."),
    (re.compile(r"secrets\.GITHUB_TOKEN", re.I), "info", "github_actions",
     "Using GITHUB_TOKEN", "Verify permissions are scoped to minimum required."),
    (re.compile(r"permissions:\s*write-all|permissions:\s*\*", re.I), "error", "github_actions",
     "Overly broad workflow permissions", "Use minimum required permissions: read for contents, write only where needed."),
    (re.compile(r"continue-on-error:\s*true", re.I), "warning", "github_actions",
     "continue-on-error: true — failures silently ignored", "Remove unless explicitly needed for flaky steps."),
    (re.compile(r"\$\{\{\s*github\.event\.issue\.title\s*\}\}|\$\{\{\s*github\.event\.pull_request\.", re.I), "warning", "github_actions",
     "Untrusted PR/issue data used in workflow", "Use contexts carefully; avoid running untrusted code."),
    # GitLab CI
    (re.compile(r"retry:\s*\d", re.I), "info", "gitlab_ci",
     "Retry configured", "Good — improves resilience."),
    (re.compile(r"allow_failure:\s*true", re.I), "warning", "gitlab_ci",
     "allow_failure: true — job failures ignored", "Remove unless explicitly needed."),
    (re.compile(r"when:\s*manual", re.I), "info", "gitlab_ci",
     "Manual gate configured", "Good — prevents accidental production deployments."),
    (re.compile(r"variables:\s*\n.*\s+(PASSWORD|SECRET|TOKEN|KEY):", re.I | re.M), "error", "gitlab_ci",
     "Possible secret in plain-text variable block", "Use GitLab CI/CD masked/protected variables instead."),
    # Jenkins
    (re.compile(r"timeout\s*\(", re.I), "info", "jenkins",
     "Build timeout configured", "Good — prevents runaway builds."),
    (re.compile(r"withCredentials\(", re.I), "info", "jenkins",
     "withCredentials block — credentials injected at runtime", "Good practice."),
    (re.compile(r"sh\s+['\"].*\$\{env\.", re.I), "warning", "jenkins",
     "Environment variable interpolation in sh step — possible injection", "Validate inputs; use returnStdout=true and trim()."),
    (re.compile(r"agent\s+none", re.I), "info", "jenkins",
     "No default agent — each stage specifies its own", "Ensure each stage has an agent block."),
    # Generic / All
    (re.compile(r"(PASSWORD|SECRET|TOKEN|API_KEY)\s*[:=]\s*['\"]?\S{6,}", re.I), "error", "generic",
     "Possible hardcoded secret in pipeline config", "Use the CI/CD platform's secrets management (GitHub Secrets, GitLab masked vars, Jenkins credentials)."),
    (re.compile(r"curl\s+.*\|\s*(ba)?sh", re.I), "error", "generic",
     "Piping remote script to shell in CI step", "Download and inspect script before execution."),
    (re.compile(r"npm\s+install\s*$", re.I), "warning", "generic",
     "npm install without --frozen-lockfile or --ci", "Use npm ci for reproducible installs."),
    (re.compile(r"pip\s+install\s+(?!-r)", re.I), "warning", "generic",
     "pip install without requirements file", "Pin dependencies in requirements.txt or pyproject.toml."),
    (re.compile(r"docker\s+build\b(?!.*--no-cache)", re.I), "warning", "generic",
     "Docker build without explicit cache strategy", "Consider --cache-from or BuildKit cache mounts."),
    (re.compile(r"(deploy|push|apply|release).*production|production.*(deploy|push|apply|release)", re.I), "warning", "generic",
     "Production deployment detected", "Ensure approval gate / manual trigger is required before production."),
]


def analyze_cicd(yaml_text: str, ci_type: str = "auto") -> Dict[str, Any]:
    """
    MCP-compatible stateless tool: analyse CI/CD pipeline configuration.
    Input is treated as plain text — NEVER executed.
    """
    if not yaml_text or not yaml_text.strip():
        return {"findings": [], "summary": "No CI/CD config provided.", "severity": "low"}

    detected_type = ci_type if ci_type != "auto" else _detect_cicd_type(yaml_text)
    lines = yaml_text.splitlines()
    findings: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for i, line in enumerate(lines):
        for pattern, ftype, applies_to, desc, rec in _PATTERNS:
            if applies_to not in (detected_type, "generic"):
                continue
            if ftype == "info":
                continue
            if pattern.search(line):
                key = f"{ftype}:{desc[:60]}"
                if key not in seen:
                    seen.add(key)
                    findings.append({
                        "finding_type": ftype,
                        "location": f"line {i + 1}: {line.strip()[:120]}",
                        "description": desc,
                        "recommendation": rec,
                    })
                break

    # YAML structure checks (GitHub Actions)
    if detected_type == "github_actions" and _YAML_OK:
        try:
            doc = yaml.safe_load(yaml_text) or {}
            jobs = doc.get("jobs", {}) or {}
            for job_name, job in jobs.items():
                if isinstance(job, dict):
                    if not job.get("timeout-minutes"):
                        findings.append({
                            "finding_type": "warning",
                            "location": f"jobs.{job_name}",
                            "description": "No timeout-minutes set on job — build may run indefinitely",
                            "recommendation": "Add timeout-minutes: 30 (or appropriate value).",
                        })
                    env = job.get("env", {}) or {}
                    for k in env:
                        if any(s in k.upper() for s in ("SECRET", "PASSWORD", "TOKEN", "KEY")):
                            findings.append({
                                "finding_type": "error",
                                "location": f"jobs.{job_name}.env.{k}",
                                "description": f"Possible secret '{k}' in job env block",
                                "recommendation": "Use ${{ secrets.MY_SECRET }} instead of plain values.",
                            })
        except Exception:
            pass

    severity = "low"
    if any(f["finding_type"] == "error" for f in findings):
        severity = "high"
    elif any(f["finding_type"] == "warning" for f in findings):
        severity = "medium"

    return {
        "findings": findings,
        "pipeline_type": detected_type,
        "summary": (
            f"Analysed {detected_type} pipeline config ({len(lines)} lines). "
            f"Found {len(findings)} issue(s). Severity: {severity}."
        ),
        "severity": severity,
    }
