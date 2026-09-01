"""Application configuration via pydantic-settings."""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file: api/core/config.py → ../../.env
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")

    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    llm_model: str = Field(default="llama3-70b-8192", alias="LLM_MODEL")

    # Groq-specific rate-limit retry
    groq_max_retries: int = Field(default=3, alias="GROQ_MAX_RETRIES")
    groq_retry_delay: float = Field(default=2.0, alias="GROQ_RETRY_DELAY")

    # ── Security ─────────────────────────────────────────────────────────────
    state_secret: str = Field(default="", alias="STATE_SECRET")
    allowed_file_types: list[str] = [".txt", ".log", ".yaml", ".yml", ".tf", ".json", ".md"]

    # ── Input limits (bytes) ─────────────────────────────────────────────────
    max_log_size: int = Field(default=50_000, alias="MAX_LOG_SIZE")
    max_config_size: int = Field(default=30_000, alias="MAX_CONFIG_SIZE")
    max_description_size: int = Field(default=5_000, alias="MAX_DESCRIPTION_SIZE")
    max_upload_size: int = Field(default=100_000, alias="MAX_UPLOAD_SIZE")

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    app_name: str = "agentic-devops-assistant"
    app_version: str = "1.0.0"

    # ── Runbooks path ────────────────────────────────────────────────────────
    runbooks_path: str = Field(default="runbooks", alias="RUNBOOKS_PATH")

    @field_validator("state_secret", mode="before")
    @classmethod
    def ensure_state_secret(cls, v: str) -> str:
        if not v:
            # Auto-generate a stable secret derived from process; stable per process
            return os.environ.get("_CACHED_STATE_SECRET", secrets.token_hex(32))
        return v

    @property
    def llm_configured(self) -> bool:
        """True if the active provider has an API key."""
        if self.llm_provider == "groq":
            return bool(self.groq_api_key)
        if self.llm_provider == "gemini":
            return bool(self.google_api_key)
        if self.llm_provider == "openrouter":
            return bool(self.openrouter_api_key)
        return False

    @property
    def active_api_key(self) -> Optional[str]:
        """Return the API key for the active provider — never expose to frontend."""
        if self.llm_provider == "groq":
            return self.groq_api_key
        if self.llm_provider == "gemini":
            return self.google_api_key
        if self.llm_provider == "openrouter":
            return self.openrouter_api_key
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Read .env with pure Python and inject into os.environ.
    # This is the most reliable approach regardless of dotenv/pydantic-settings versions.
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip()
    return Settings()
