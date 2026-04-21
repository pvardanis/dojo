# ABOUTME: Structlog + stdlib logging configuration.
# ABOUTME: Dev → ConsoleRenderer; prod → JSONRenderer; tests → WARNING.
"""Structlog + stdlib logging configuration for Dojo."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog + stdlib logging once at app startup."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    processors: list[structlog.typing.Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if os.getenv("DOJO_ENV", "dev") == "prod":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Idempotent configure without the RuntimeWarning that
    # structlog.configure_once() emits — under filterwarnings=error
    # that warning escalates to a test failure when anything calls
    # configure_logging a second time in the same process (e.g. the
    # lifespan smoke test after test_logging_smoke runs).
    if not structlog.is_configured():
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> Any:
    """Return a module-bound structlog logger.

    Every module uses `log = get_logger(__name__)` — identical
    ergonomics to stdlib logging, structlog's structure underneath.
    """
    return structlog.get_logger(name)
