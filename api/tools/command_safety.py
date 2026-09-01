"""MCP-compatible tool: dangerous command detection and safety policy enforcement."""
from __future__ import annotations

import re
from typing import Any, Dict, List

# ── Dangerous / destructive patterns ─────────────────────────────────────────
_DANGEROUS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\brm\s+(-[rRfF]{1,3})\b"), "Recursive/forced deletion", "critical"),
    (re.compile(r"\bdd\s+if="), "Raw disk write", "critical"),
    (re.compile(r"\bmkfs\b"), "Filesystem format", "critical"),
    (re.compile(r"\bfdisk\b|\bparted\b"), "Partition table modification", "critical"),
    (re.compile(r"\bshred\b|\bwipe\b"), "Secure file erase", "critical"),
    (re.compile(r"\bterraform\s+apply\b"), "Terraform infrastructure apply", "high"),
    (re.compile(r"\bterraform\s+destroy\b"), "Terraform infrastructure destroy", "critical"),
    (re.compile(r"\bkubectl\s+delete\b"), "Kubernetes resource deletion", "high"),
    (re.compile(r"\bkubectl\s+apply\b"), "Kubernetes resource apply", "high"),
    (re.compile(r"\bkubectl\s+patch\b|\bkubectl\s+edit\b"), "Kubernetes resource modification", "high"),
    (re.compile(r"\baws\s+.*\s+terminate\b"), "AWS resource termination", "critical"),
    (re.compile(r"\baws\s+.*\s+delete\b"), "AWS resource deletion", "high"),
    (re.compile(r"\baws\s+s3\s+rm\b"), "S3 object deletion", "high"),
    (re.compile(r"\baz\s+.*\s+delete\b"), "Azure resource deletion", "high"),
    (re.compile(r"\bgcloud\s+.*\s+delete\b"), "GCP resource deletion", "high"),
    (re.compile(r"DROP\s+(DATABASE|TABLE|SCHEMA|INDEX)", re.I), "Database object drop", "critical"),
    (re.compile(r"TRUNCATE\s+TABLE", re.I), "Table truncation", "critical"),
    (re.compile(r"DELETE\s+FROM\s+\w+\s*;", re.I), "Unqualified table delete", "high"),
    (re.compile(r"\bcurl\b.+\|\s*(ba)?sh\b"), "Piped remote script execution", "critical"),
    (re.compile(r"\bwget\b.+\|\s*(ba)?sh\b"), "Piped remote script execution", "critical"),
    (re.compile(r"\bchmod\s+(-R\s+)?777\b"), "Insecure world-writable permissions", "high"),
    (re.compile(r"\bchown\s+-R\b"), "Recursive ownership change", "medium"),
    (re.compile(r"\bsystemctl\s+(stop|disable|mask)\b"), "Service disruption", "high"),
    (re.compile(r"\bservice\s+\w+\s+stop\b"), "Service stop", "high"),
    (re.compile(r"\bpkill\b|\bkillall\b"), "Mass process termination", "high"),
    (re.compile(r">\s*/dev/(sd[a-z]+|nvme\w+|hd[a-z]+)"), "Direct disk device write", "critical"),
    (re.compile(r"\beval\s*\(|\beval\s+[\"'`]"), "Dynamic code evaluation", "critical"),
    (re.compile(r"\bbase64\b.*\|\s*(ba)?sh\b"), "Encoded remote code execution", "critical"),
    (re.compile(r"\bnohup\b.+&\s*$"), "Detached background process", "medium"),
    (re.compile(r"\biptables\s+-F\b|\bufw\s+disable\b"), "Firewall flush/disable", "critical"),
    (re.compile(r"\bpasswd\b.*--stdin\b"), "Password change via stdin", "high"),
    (re.compile(r"\bhistory\s+-c\b"), "Shell history erasure", "high"),
]

# ── Explicitly safe read-only patterns ────────────────────────────────────────
_SAFE_READONLY: list[re.Pattern[str]] = [
    re.compile(r"^\s*kubectl\s+(get|describe|logs|top|explain|version|cluster-info)\b"),
    re.compile(r"^\s*terraform\s+(plan|show|validate|fmt|output|version|state\s+(list|show|pull))\b"),
    re.compile(r"^\s*aws\s+.*(describe|list|get|show|status)\b"),
    re.compile(r"^\s*az\s+.*(show|list|get|describe)\b"),
    re.compile(r"^\s*gcloud\s+.*(describe|list|get)\b"),
    re.compile(r"^\s*(cat|less|more|head|tail|grep|awk|sed|sort|uniq|wc)\b"),
    re.compile(r"^\s*(df|du|free|top|htop|ps|vmstat|iostat|netstat|ss|ifconfig|ip\s+addr)\b"),
    re.compile(r"^\s*(curl\s+(-s\s+)?-I|curl\s+(-s\s+)?--head)\b"),
    re.compile(r"^\s*(dig|nslookup|host|ping\s+-c|traceroute|mtr)\b"),
    re.compile(r"^\s*(journalctl|dmesg)\b"),
    re.compile(r"^\s*systemctl\s+(status|is-active|is-enabled|list-units)\b"),
    re.compile(r"^\s*docker\s+(ps|logs|inspect|stats|images|info|version|events)\b"),
    re.compile(r"^\s*helm\s+(list|status|get|version|history|show)\b"),
    re.compile(r"^\s*SELECT\s+", re.I),
    re.compile(r"^\s*EXPLAIN\s+", re.I),
    re.compile(r"^\s*(openssl\s+(s_client|verify|x509|crl|pkcs12))\b"),
]


def check_command_safety(command: str) -> Dict[str, Any]:
    """
    MCP-compatible stateless tool: evaluate a shell command for safety.

    Returns:
        dict with keys: command, is_dangerous, is_readonly, risk_level,
                        requires_approval, reasons, recommendation
    """
    reasons: list[str] = []
    highest_risk = "low"

    _RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for pattern, reason, risk in _DANGEROUS:
        if pattern.search(command):
            reasons.append(f"{reason} [{risk.upper()}]")
            if _RISK_ORDER.get(risk, 0) > _RISK_ORDER.get(highest_risk, 0):
                highest_risk = risk

    is_readonly = any(p.search(command) for p in _SAFE_READONLY) and not reasons
    is_dangerous = bool(reasons)

    # If not explicitly safe and not dangerous, treat as medium risk
    if not is_dangerous and not is_readonly:
        highest_risk = "medium"

    requires_approval = highest_risk in ("high", "critical")

    if requires_approval:
        recommendation = (
            "⛔ DO NOT execute without explicit operator approval, a change-management ticket, "
            "and a tested rollback plan. This command may cause irreversible changes."
        )
    elif highest_risk == "medium":
        recommendation = (
            "⚠️ Review carefully before running. Not confirmed read-only. "
            "Test in a non-production environment first."
        )
    else:
        recommendation = "✅ Safe to run as a read-only diagnostic command."

    return {
        "command": command,
        "is_dangerous": is_dangerous,
        "is_readonly": is_readonly,
        "risk_level": highest_risk,
        "requires_approval": requires_approval,
        "reasons": reasons,
        "recommendation": recommendation,
    }


def batch_check(commands: List[str]) -> List[Dict[str, Any]]:
    """Check a list of commands and return results."""
    return [check_command_safety(c) for c in commands]
