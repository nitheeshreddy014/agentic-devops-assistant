"""LLM provider abstraction: Groq (default), Gemini, OpenRouter."""
from __future__ import annotations

import logging
import time
from typing import Optional

from langchain_core.language_models import BaseChatModel

from api.core.config import get_settings
from api.core.logging_config import get_logger

logger = get_logger(__name__)


def get_llm(temperature: float = 0.1) -> Optional[BaseChatModel]:
    """
    Return a configured chat LLM or None if no API key is present.
    Groq is the default provider. Google Gemini and OpenRouter are optional.
    The app degrades gracefully when None is returned.
    """
    settings = get_settings()

    if not settings.llm_configured:
        logger.warning(
            "LLM not configured",
            extra={"provider": settings.llm_provider, "model": settings.llm_model},
        )
        return None

    provider = settings.llm_provider.lower()

    try:
        if provider == "groq":
            return _build_groq(settings, temperature)
        if provider == "gemini":
            return _build_gemini(settings, temperature)
        if provider == "openrouter":
            return _build_openrouter(settings, temperature)
    except Exception as exc:
        logger.error(f"Failed to initialise LLM provider '{provider}': {exc}")
        return None

    logger.warning(f"Unknown LLM provider '{provider}'. Supported: groq, gemini, openrouter.")
    return None


# ── Groq ──────────────────────────────────────────────────────────────────────

def _build_groq(settings, temperature: float) -> BaseChatModel:
    from langchain_groq import ChatGroq  # type: ignore[import]

    # Use configured model, fall back to llama3-70b-8192 if not set
    model = settings.llm_model or "llama3-70b-8192"

    logger.info(f"Initialising Groq LLM: model={model}")
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name=model,
        temperature=temperature,
        max_retries=settings.groq_max_retries,
    )


# ── Google Gemini (optional) ─────────────────────────────────────────────────

def _build_gemini(settings, temperature: float) -> BaseChatModel:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "Install langchain-google-genai to use Gemini: "
            "pip install langchain-google-genai"
        ) from exc

    model = settings.llm_model if settings.llm_model != "llama-3.3-70b-versatile" else "gemini-1.5-flash"
    logger.info("Initialising Google Gemini LLM", extra={"model": model})
    return ChatGoogleGenerativeAI(
        google_api_key=settings.google_api_key,
        model=model,
        temperature=temperature,
    )


# ── OpenRouter (optional) ────────────────────────────────────────────────────

def _build_openrouter(settings, temperature: float) -> BaseChatModel:
    try:
        from langchain_openai import ChatOpenAI  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "Install langchain-openai to use OpenRouter: "
            "pip install langchain-openai"
        ) from exc

    model = settings.llm_model if settings.llm_model != "llama-3.3-70b-versatile" else "meta-llama/llama-3.3-70b-instruct"
    logger.info("Initialising OpenRouter LLM", extra={"model": model})
    return ChatOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        model=model,
        temperature=temperature,
        max_retries=3,
    )


# ── Rate-limit helper ────────────────────────────────────────────────────────

def invoke_with_retry(llm: BaseChatModel, messages, max_retries: int = 3, base_delay: float = 2.0):
    """
    Invoke LLM with exponential backoff on HTTP 429 (rate limit).
    Immediately raises on permission/network-block errors (no retries).
    Raises the last exception if all retries fail.
    """
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as exc:
            err_str = str(exc).lower()
            raw_str = str(exc)  # preserve original casing for logging

            is_rate_limit  = "429" in err_str or "rate limit" in err_str or "rate_limit" in err_str
            is_blocked     = (
                "permissiondenied" in err_str.replace(" ", "")
                or "403" in err_str
                or "zscaler" in err_str
                or "not allowed" in err_str
                or "firewall" in err_str
                or "blocked" in err_str
            )
            is_network_err = "connection" in err_str or "timeout" in err_str or "unreachable" in err_str
            is_model_404   = ("404" in err_str and "does not exist" in err_str) or "not have access" in err_str

            if is_model_404:
                # Try fallback model automatically
                logger.warning(f"Model not available (404). Trying llama3-70b-8192 fallback.")
                from langchain_groq import ChatGroq  # type: ignore[import]
                try:
                    fallback_llm = ChatGroq(
                        groq_api_key=llm.groq_api_key if hasattr(llm, 'groq_api_key') else None,
                        model_name="llama3-70b-8192",
                        temperature=0.1,
                        max_retries=2,
                    )
                    return fallback_llm.invoke(messages)
                except Exception:
                    raise exc
            if is_blocked:
                logger.error(
                    "LLM request blocked by network/firewall (not retrying). "
                    f"Detail: {raw_str[:300]}"
                )
                raise
            if is_network_err and attempt >= 1:
                logger.error(f"LLM network error after {attempt+1} attempts: {raw_str[:200]}")
                raise
            if is_rate_limit and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Groq rate limit hit (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("All retries exhausted")
