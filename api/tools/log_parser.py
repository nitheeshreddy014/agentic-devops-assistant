"""MCP-compatible tool: log-text analysis without LLM execution."""
from __future__ import annotations

import re
from typing import Any, Dict, List

# ── Error-pattern library ────────────────────────────────────────────────────
_PATTERNS: list[tuple[re.Pattern[str], str, str, bool]] = [
    # (pattern, level, implication, is_root_indicator)
    # Kubernetes
    (re.compile(r"\bCrashLoopBackOff\b"), "ERROR", "Pod keeps crashing and restarting", True),
    (re.compile(r"\bOOMKilled\b"), "CRITICAL", "Container killed — out of memory", True),
    (re.compile(r"\bImagePullBackOff\b|\bErrImagePull\b"), "ERROR", "Cannot pull container image", True),
    (re.compile(r"\bUnschedulable\b"), "ERROR", "Pod cannot be scheduled — resource or taint issue", True),
    (re.compile(r"\bContainerCreating\b"), "WARNING", "Container stuck in creating state", False),
    (re.compile(r"\bBackOff\b"), "WARNING", "Kubernetes back-off event", False),
    (re.compile(r"\bFailed to pull image\b", re.I), "ERROR", "Container image pull failure", True),
    (re.compile(r"\bliveness probe failed\b", re.I), "ERROR", "Liveness probe failing — pod will restart", True),
    (re.compile(r"\breadiness probe failed\b", re.I), "WARNING", "Readiness probe failing — pod removed from service", False),
    # AWS
    (re.compile(r"\bAccessDenied\b|\bUnauthorizedAccess\b"), "ERROR", "IAM permission denied", True),
    (re.compile(r"\bThrottlingException\b|\bRequestLimitExceeded\b"), "WARNING", "AWS API rate limiting", False),
    (re.compile(r"\bResourceNotFoundException\b|\bNoSuchBucket\b"), "ERROR", "AWS resource not found", True),
    (re.compile(r"\bExpiredTokenException\b|\bTokenExpiredException\b"), "ERROR", "AWS credentials expired", True),
    (re.compile(r"\bInvalidClientTokenId\b"), "ERROR", "Invalid AWS access key", True),
    # Terraform
    (re.compile(r"\bError acquiring the state lock\b", re.I), "ERROR", "Terraform state lock held by another process", True),
    (re.compile(r"\bstate lock\b", re.I), "ERROR", "Terraform state locking issue", True),
    (re.compile(r"\bError: .*\n.*\│", re.DOTALL), "ERROR", "Terraform provider/resource error", True),
    (re.compile(r"\bProvider produced inconsistent result\b", re.I), "ERROR", "Terraform provider bug or state drift", True),
    # Docker
    (re.compile(r"\bexit(?:ed)? (?:code |status )?[1-9]\d*\b", re.I), "ERROR", "Process exited with non-zero status", True),
    (re.compile(r"\bno such file or directory\b", re.I), "ERROR", "Required file or binary missing", True),
    (re.compile(r"\bpermission denied\b", re.I), "ERROR", "File or socket permission denied", True),
    (re.compile(r"\bCannot connect to the Docker daemon\b", re.I), "ERROR", "Docker daemon not running", True),
    (re.compile(r"\bnetwork .* not found\b", re.I), "ERROR", "Docker network missing", True),
    # Network
    (re.compile(r"\bConnection refused\b", re.I), "ERROR", "Service not accepting connections on that port", True),
    (re.compile(r"\bETIMEDOUT\b|\bconnection timed out\b", re.I), "ERROR", "Network connection timed out", True),
    (re.compile(r"\bECONNREFUSED\b"), "ERROR", "TCP connection refused", True),
    (re.compile(r"\bName or service not known\b|\bDNS.*resolv\b", re.I), "ERROR", "DNS resolution failure", True),
    (re.compile(r"\bNo route to host\b", re.I), "ERROR", "Network routing failure", True),
    # Database
    (re.compile(r"\bToo many connections\b|\bmax_connections\b", re.I), "ERROR", "Database connection pool exhausted", True),
    (re.compile(r"\bdeadlock detected\b", re.I), "ERROR", "Database deadlock — transactions blocking each other", True),
    (re.compile(r"\bConnection reset by peer\b", re.I), "ERROR", "Database connection dropped mid-query", True),
    (re.compile(r"\bfatal.*authentication.*failed\b", re.I), "ERROR", "Database authentication failure", True),
    # SSL/TLS
    (re.compile(r"\bcertificate.*expired\b|\bexpired.*certificate\b", re.I), "ERROR", "SSL certificate expired", True),
    (re.compile(r"\bSSL.*handshake.*fail\b|\bTLS.*handshake.*fail\b", re.I), "ERROR", "SSL/TLS handshake failure", True),
    (re.compile(r"\bcertificate.*verify.*fail\b", re.I), "ERROR", "SSL certificate verification failure", True),
    (re.compile(r"\bself.signed certificate\b", re.I), "WARNING", "Self-signed certificate in use", False),
    # CI/CD
    (re.compile(r"\bBuild FAILED\b|\bBUILD FAILURE\b", re.I), "ERROR", "Build step failed", True),
    (re.compile(r"\bnpm ERR!\b|\byarn error\b", re.I), "ERROR", "Node.js package manager error", True),
    (re.compile(r"\bFAILED\s+\d+\s+test\b|\d+\s+test.*failed\b", re.I), "ERROR", "Test failures in CI", True),
    (re.compile(r"\boutOfMemoryError\b", re.I), "CRITICAL", "JVM or process out of memory", True),
    # Linux/System
    (re.compile(r"\bNo space left on device\b", re.I), "CRITICAL", "Disk full — writes failing", True),
    (re.compile(r"\bkill(?:ed by signal|ed)?\s+9\b", re.I), "CRITICAL", "Process killed — SIGKILL (OOM or manual)", True),
    (re.compile(r"\bLoad average\s+[\d.]+\s+[\d.]+\s+[\d.]+"), "WARNING", "System load statistics detected", False),
    (re.compile(r"\bsegfault\b|\bsegmentation fault\b", re.I), "CRITICAL", "Process segmentation fault", True),
    (re.compile(r"\bkernel BUG\b", re.I), "CRITICAL", "Linux kernel bug", True),
    # General
    (re.compile(r"\b(FATAL|fatal)\b"), "CRITICAL", "Fatal error condition", True),
    (re.compile(r"\b(ERROR|error)\b(?!\s+(code|level|log))"), "ERROR", "Error condition", False),
    (re.compile(r"\b(WARN|WARNING|warn)\b"), "WARNING", "Warning condition", False),
    (re.compile(r"\bpanic:\b", re.I), "CRITICAL", "Go/application panic", True),
    (re.compile(r"\bException in thread\b|\bUncaughtException\b"), "ERROR", "Unhandled exception", True),
    (re.compile(r"\bStack trace\b|\btraceback\b", re.I), "ERROR", "Exception stack trace", False),
]

# ── Error-code extractors ────────────────────────────────────────────────────
_CODE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(AKIA[A-Z0-9]{16})\b"),             # AWS key (redacted upstream)
    re.compile(r"\bHTTP\s+([45]\d{2})\b", re.I),       # HTTP error codes
    re.compile(r"\bstatus\s+([45]\d{2})\b", re.I),
    re.compile(r"\b(E[A-Z]{3,10})\b"),                  # errno-style codes
    re.compile(r"\b(CrashLoopBackOff|OOMKilled|ImagePullBackOff|Unschedulable|Pending|Evicted)\b"),
    re.compile(r"\b(AccessDenied|ThrottlingException|ExpiredTokenException|InvalidClientTokenId)\b"),
    re.compile(r"\b(ECONNREFUSED|ETIMEDOUT|ECONNRESET|EHOSTUNREACH|ENOTFOUND)\b"),
    re.compile(r"\b(TF-\w+)\b"),                        # Terraform error codes
]

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_LEVEL_SEVERITY = {
    "CRITICAL": "critical",
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
}


def parse_logs(log_text: str, technology: str = "unknown") -> Dict[str, Any]:
    """
    MCP-compatible stateless tool: parse log text and return structured findings.
    The log content is NEVER executed — it is treated as plain text.
    """
    if not log_text or not log_text.strip():
        return {
            "findings": [],
            "summary": "No logs provided.",
            "severity": "low",
            "error_codes": [],
            "total_lines": 0,
            "error_count": 0,
            "warning_count": 0,
        }

    lines = log_text.splitlines()
    findings: List[Dict[str, Any]] = []
    seen: set[str] = set()
    error_codes: set[str] = set()

    # Extract error codes globally
    for cp in _CODE_PATTERNS:
        for m in cp.findall(log_text):
            code = m if isinstance(m, str) else m[0]
            if code and len(code) > 2:
                error_codes.add(code)

    # Per-line analysis
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        for pattern, level, implication, is_root in _PATTERNS:
            if not pattern.search(line):
                continue
            dedup_key = f"{level}:{stripped[:100]}"
            if dedup_key in seen:
                break
            seen.add(dedup_key)

            ctx_start = max(0, i - 1)
            ctx_end = min(len(lines), i + 4)
            context = "\n".join(lines[ctx_start:ctx_end])

            findings.append({
                "level": level,
                "message": stripped[:300],
                "line_number": i + 1,
                "context": context[:600],
                "implication": implication,
                "is_root_indicator": is_root,
            })
            break  # only first matching pattern per line

    # Overall severity
    if any(f["level"] == "CRITICAL" for f in findings):
        overall = "critical"
    elif any(f["level"] == "ERROR" for f in findings):
        overall = "high"
    elif any(f["level"] == "WARNING" for f in findings):
        overall = "medium"
    else:
        overall = "low"

    err_c = sum(1 for f in findings if f["level"] in ("ERROR", "CRITICAL"))
    warn_c = sum(1 for f in findings if f["level"] == "WARNING")

    return {
        "findings": findings[:60],
        "summary": (
            f"Analysed {len(lines)} log lines ({technology}). "
            f"Found {err_c} error(s) and {warn_c} warning(s). "
            f"Overall severity: {overall}."
        ),
        "severity": overall,
        "error_codes": sorted(error_codes),
        "total_lines": len(lines),
        "error_count": err_c,
        "warning_count": warn_c,
    }
