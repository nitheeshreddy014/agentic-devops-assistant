"""Security utilities: state signing, secret redaction, input validation."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import uuid
from typing import Any

from api.core.config import get_settings

# ── Patterns for redacting secrets from user-supplied text ────────────────────
_REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'(?i)(password\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(passwd\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(secret\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(token\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(api[_-]?key\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(access[_-]?key\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(secret[_-]?key\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(private[_-]?key\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(client[_-]?secret\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)(auth[_-]?token\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    # AWS patterns
    (re.compile(r'(AKIA[A-Z0-9]{16})'), '[AWS_KEY_REDACTED]'),
    (re.compile(r'(?i)(aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*)\S+'), r'\1[REDACTED]'),
    # Private key blocks
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----',
                re.DOTALL), '[PRIVATE_KEY_REDACTED]'),
    # Generic bearer tokens
    (re.compile(r'(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*'), 'Bearer [REDACTED]'),
    # Connection strings with passwords
    (re.compile(r'(?i)(mongodb|postgresql|mysql|redis)://[^:]+:[^@]+@'), r'\1://[REDACTED]:[REDACTED]@'),
]

# ── Dangerous command patterns (destructive / irreversible) ────────────────────
_DANGEROUS_COMMAND_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'\brm\s+-rf?\b'),
    re.compile(r'\bdd\s+if='),
    re.compile(r'\bmkfs\b'),
    re.compile(r'\bfdisk\b'),
    re.compile(r'\bshred\b'),
    re.compile(r'\bterraform\s+apply\b'),
    re.compile(r'\bterraform\s+destroy\b'),
    re.compile(r'\bkubectl\s+delete\b'),
    re.compile(r'\bkubectl\s+apply\b'),
    re.compile(r'\baws\s+ec2\s+terminate\b'),
    re.compile(r'\baws\s+s3\s+rm\b'),
    re.compile(r'\baz\s+.*\s+delete\b'),
    re.compile(r'\bgcloud\s+.*\s+delete\b'),
    re.compile(r'\bdrop\s+database\b', re.IGNORECASE),
    re.compile(r'\bdrop\s+table\b', re.IGNORECASE),
    re.compile(r'\btruncate\s+table\b', re.IGNORECASE),
    re.compile(r'>\s*/dev/sda'),
    re.compile(r'\bchmod\s+-R\s+777\b'),
    re.compile(r'\bsystemctl\s+(stop|disable)\b'),
    re.compile(r'\bservice\s+\w+\s+stop\b'),
    re.compile(r'\bpkill\b'),
    re.compile(r'\bkillall\b'),
    re.compile(r'\bnohup.*&\s*$'),
    re.compile(r'\bcurl\s+.*\|\s*(bash|sh)\b'),
    re.compile(r'\bwget\s+.*\|\s*(bash|sh)\b'),
    re.compile(r'eval\s*\('),
    re.compile(r'\bbase64\s+--decode\b.*\|\s*(bash|sh)\b'),
]

# ── Forbidden file types (binary / executable) ────────────────────────────────
_FORBIDDEN_EXTENSIONS = {
    '.exe', '.dll', '.so', '.dylib', '.bin', '.elf',
    '.sh', '.bat', '.cmd', '.ps1', '.com', '.scr',
    '.py', '.rb', '.php', '.js', '.ts',            # executable scripts
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',  # archives
    '.jpg', '.jpeg', '.png', '.gif', '.pdf',        # binary formats
}


def redact_secrets(text: str) -> str:
    """Remove sensitive values from user-supplied text before LLM calls."""
    if not text:
        return text
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def is_dangerous_command(command: str) -> tuple[bool, list[str]]:
    """Return (is_dangerous, list_of_matched_reasons)."""
    reasons: list[str] = []
    for pat in _DANGEROUS_COMMAND_PATTERNS:
        if pat.search(command):
            reasons.append(pat.pattern)
    return bool(reasons), reasons


def validate_text_input(text: str | None, max_bytes: int, field_name: str) -> str:
    """Validate and truncate text input. Raises ValueError on policy violation."""
    if not text:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) > max_bytes:
        raise ValueError(
            f"Field '{field_name}' exceeds maximum size of {max_bytes} bytes "
            f"(received {len(encoded)} bytes). Please reduce the input."
        )
    return text.strip()


def validate_filename(filename: str) -> None:
    """Raise ValueError if file extension is not allowed."""
    import os
    ext = os.path.splitext(filename.lower())[1]
    if ext in _FORBIDDEN_EXTENSIONS:
        raise ValueError(
            f"File type '{ext}' is not permitted. "
            f"Only plain-text configuration and log files are accepted."
        )


def generate_request_id() -> str:
    return str(uuid.uuid4())


# ── Stateless investigation state signing ────────────────────────────────────

def _get_signing_key() -> bytes:
    settings = get_settings()
    return settings.state_secret.encode("utf-8")


def sign_state(state: dict[str, Any]) -> str:
    """Serialize state dict → base64(json) + HMAC signature."""
    payload = json.dumps(state, default=str, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(
        _get_signing_key(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_and_load_state(token: str) -> dict[str, Any]:
    """Verify HMAC signature and return state dict. Raises ValueError on tampering."""
    try:
        payload_b64, sig = token.rsplit(".", 1)
    except ValueError:
        raise ValueError("Invalid investigation token format.")

    expected_sig = hmac.new(
        _get_signing_key(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, sig):
        raise ValueError("Investigation token integrity check failed — possible tampering.")

    try:
        payload = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        return json.loads(payload)
    except Exception as exc:
        raise ValueError(f"Failed to decode investigation token: {exc}") from exc
