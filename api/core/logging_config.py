"""Structured JSON logging configuration."""
from __future__ import annotations

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger


class _RequestIdFilter(logging.Filter):
    """Inject request_id into every log record (default: '-')."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        if not hasattr(record, "request_id"):
            record.request_id = "-"  # type: ignore[attr-defined]
        return True


def configure_logging(level: str = "INFO") -> None:
    """Set up JSON structured logging for the application."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())

    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, extra: dict[str, Any] | None = None) -> None:
    """Emit a structured event log line."""
    logger.info(event, extra=extra or {})
