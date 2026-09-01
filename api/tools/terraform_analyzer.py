"""MCP-compatible tool: Terraform config / plan text analysis."""
from __future__ import annotations

import re
from typing import Any, Dict, List


_FINDINGS: list[tuple[re.Pattern[str], str, str, str]] = [
    # (pattern, finding_type, description_template, recommendation)
    (re.compile(r"Error acquiring the state lock", re.I),
     "error", "Terraform state lock conflict detected",
     "Run: terraform force-unlock <LOCK_ID> after confirming no other apply is running."),
    (re.compile(r"Backend initialization required", re.I),
     "error", "Backend not initialised",
     "Run: terraform init"),
    (re.compile(r"Error: .*provider", re.I),
     "error", "Provider configuration error",
     "Check provider credentials and version constraints in required_providers."),
    (re.compile(r"Error: .*authentication|credential", re.I),
     "error", "Authentication/credential error",
     "Verify cloud credentials (AWS_ACCESS_KEY_ID, ARM_CLIENT_ID, GOOGLE_CREDENTIALS, etc.)."),
    (re.compile(r"Error: .*resource.*already exists", re.I),
     "error", "Resource already exists in cloud — state drift",
     "Run: terraform import <resource_type>.<name> <cloud_id> to bring it under management."),
    (re.compile(r"Unsupported argument|An argument named", re.I),
     "error", "Unsupported or deprecated argument in configuration",
     "Check provider changelog for renamed/removed arguments."),
    (re.compile(r"This plan does nothing", re.I),
     "warning", "Plan has no changes — possibly stale cache",
     "Run: terraform refresh then re-plan."),
    (re.compile(r"Plan: \d+ to add, \d+ to change, \d+ to destroy"),
     "warning", "Destroy operations in plan",
     "Review destroy operations carefully before applying."),
    (re.compile(r"must be replaced", re.I),
     "warning", "Resource replacement required (downtime risk)",
     "Evaluate whether recreation is acceptable; consider lifecycle rules."),
    (re.compile(r"force replacement", re.I),
     "warning", "Forced replacement detected",
     "Confirm the replacement is intentional."),
    (re.compile(r"deprecated", re.I),
     "warning", "Deprecated Terraform syntax or argument",
     "Upgrade configuration to current provider API."),
    (re.compile(r"version\s*=\s*[\"']?[<>~!]+", re.I),
     "warning", "Version constraints with operators — may be overly restrictive",
     "Consider using >= with an upper bound like ~> 5.0."),
    (re.compile(r"hardcoded.*password|password\s*=\s*[\"'][^\"']{3,}", re.I),
     "error", "Possible hardcoded password in configuration",
     "Use Terraform variable with sensitive=true or a secrets manager."),
    (re.compile(r"sensitive\s*=\s*false", re.I),
     "warning", "Output or variable marked non-sensitive may expose secrets",
     "Set sensitive=true for outputs containing credentials or tokens."),
    (re.compile(r"terraform\s+{\s*required_version", re.I),
     "warning", "required_version constraint present — ensure CI Terraform version matches",
     "Pin Terraform version in CI with tfenv or asdf."),
    (re.compile(r"0\.0\.0\.0/0", re.I),
     "warning", "Wide-open CIDR 0.0.0.0/0 detected in security group / firewall rule",
     "Restrict CIDR to known IP ranges for production workloads."),
    (re.compile(r"count\s*=\s*0", re.I),
     "warning", "Resource count set to 0 — resource will be destroyed",
     "Verify this is intentional."),
    (re.compile(r"lifecycle\s*{[^}]*prevent_destroy\s*=\s*false", re.DOTALL),
     "warning", "prevent_destroy not enabled on critical resource",
     "Add lifecycle { prevent_destroy = true } for stateful resources."),
]

_RESOURCE_RE = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"')
_MODULE_RE = re.compile(r'module\s+"([^"]+)"')
_PROVIDER_RE = re.compile(r'provider\s+"([^"]+)"')
_VARIABLE_RE = re.compile(r'variable\s+"([^"]+)"')
_OUTPUT_RE = re.compile(r'output\s+"([^"]+)"')
_PLAN_SUMMARY_RE = re.compile(r"Plan:\s+(\d+) to add, (\d+) to change, (\d+) to destroy", re.I)


def analyze_terraform(config_text: str) -> Dict[str, Any]:
    """
    MCP-compatible stateless tool: analyse Terraform HCL config or plan output.
    Input is treated as plain text — NEVER executed.
    """
    if not config_text or not config_text.strip():
        return {"findings": [], "summary": "No Terraform content provided.", "severity": "low"}

    findings: List[Dict[str, Any]] = []
    lines = config_text.splitlines()

    for i, line in enumerate(lines):
        for pattern, ftype, desc, rec in _FINDINGS:
            if pattern.search(line):
                findings.append({
                    "finding_type": ftype,
                    "location": f"line {i + 1}: {line.strip()[:120]}",
                    "description": desc,
                    "recommendation": rec,
                })
                break

    # Extract structural information
    resources = [f"{m[0]}.{m[1]}" for m in _RESOURCE_RE.findall(config_text)]
    modules = _MODULE_RE.findall(config_text)
    providers = _PROVIDER_RE.findall(config_text)
    variables = _VARIABLE_RE.findall(config_text)
    outputs = _OUTPUT_RE.findall(config_text)

    # Plan summary
    plan_summary = None
    pm = _PLAN_SUMMARY_RE.search(config_text)
    if pm:
        plan_summary = {
            "add": int(pm.group(1)),
            "change": int(pm.group(2)),
            "destroy": int(pm.group(3)),
        }

    severity = "low"
    if any(f["finding_type"] == "error" for f in findings):
        severity = "high"
    elif any(f["finding_type"] == "warning" for f in findings):
        severity = "medium"

    summary = (
        f"Analysed Terraform content: {len(resources)} resource(s), "
        f"{len(modules)} module(s), {len(providers)} provider(s). "
        f"Found {len(findings)} issue(s). Severity: {severity}."
    )
    if plan_summary:
        summary += (
            f" Plan: +{plan_summary['add']} ~{plan_summary['change']} "
            f"-{plan_summary['destroy']}."
        )

    return {
        "findings": findings,
        "resources": resources,
        "modules": modules,
        "providers": providers,
        "variables": variables,
        "outputs": outputs,
        "plan_summary": plan_summary,
        "summary": summary,
        "severity": severity,
    }
