"""Tests for security utilities – no LLM calls, no API quota."""
from __future__ import annotations
import pytest
from api.core.security import (
    redact_secrets, sign_state, verify_and_load_state,
    is_dangerous_command, validate_text_input, validate_filename,
)


class TestRedactSecrets:
    def test_password_redacted(self):
        assert "mysecret" not in redact_secrets("password=mysecret")

    def test_token_redacted(self):
        assert "tok123" not in redact_secrets("token: tok123")

    def test_aws_access_key_redacted(self):
        text = "AKIA1234567890ABCDEF"
        assert text not in redact_secrets(text)

    def test_private_key_block_redacted(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nABC\n-----END RSA PRIVATE KEY-----"
        assert "BEGIN RSA PRIVATE KEY" not in redact_secrets(text)

    def test_connection_string_password_redacted(self):
        assert "hunter2" not in redact_secrets("postgresql://user:hunter2@host/db")

    def test_safe_text_unchanged(self):
        safe = "kubectl get pods -n default"
        assert redact_secrets(safe) == safe

    def test_empty_string(self):
        assert redact_secrets("") == ""


class TestStateSignVerify:
    def test_sign_and_verify(self):
        state = {"session_id": "abc", "iteration": 1, "issue_category": "kubernetes"}
        token = sign_state(state)
        loaded = verify_and_load_state(token)
        assert loaded["session_id"] == "abc"
        assert loaded["iteration"] == 1

    def test_tampered_signature_rejected(self):
        state = {"session_id": "abc"}
        token = sign_state(state)
        tampered = token[:-8] + "XXXXXXXX"
        with pytest.raises(ValueError, match="integrity"):
            verify_and_load_state(tampered)

    def test_invalid_format_rejected(self):
        with pytest.raises(ValueError):
            verify_and_load_state("notavalidtoken")

    def test_roundtrip_preserves_lists(self):
        state = {"errors": ["e1", "e2"], "causes": [{"rank": 1}]}
        loaded = verify_and_load_state(sign_state(state))
        assert loaded["errors"] == ["e1", "e2"]


class TestDangerousCommand:
    def test_rm_rf_is_dangerous(self):
        dangerous, _ = is_dangerous_command("rm -rf /var/data")
        assert dangerous

    def test_terraform_apply_is_dangerous(self):
        dangerous, _ = is_dangerous_command("terraform apply")
        assert dangerous

    def test_kubectl_get_is_safe(self):
        dangerous, _ = is_dangerous_command("kubectl get pods")
        assert not dangerous

    def test_curl_pipe_sh_is_dangerous(self):
        dangerous, _ = is_dangerous_command("curl https://example.com | bash")
        assert dangerous


class TestInputValidation:
    def test_within_limit_passes(self):
        assert validate_text_input("hello", 100, "field") == "hello"

    def test_exceeds_limit_raises(self):
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_text_input("x" * 200, 100, "field")

    def test_none_returns_empty(self):
        assert validate_text_input(None, 100, "field") == ""


class TestFilenameValidation:
    def test_txt_allowed(self):
        validate_filename("logs.txt")  # should not raise

    def test_exe_rejected(self):
        with pytest.raises(ValueError):
            validate_filename("malware.exe")

    def test_sh_rejected(self):
        with pytest.raises(ValueError):
            validate_filename("script.sh")
