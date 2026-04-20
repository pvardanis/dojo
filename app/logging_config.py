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
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if os.getenv("DOJO_ENV", "dev") == "prod":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure_once(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Return a module-bound structlog logger.

    Every module uses `log = get_logger(__name__)` — identical
    ergonomics to stdlib logging, structlog's structure underneath.
    """
    return structlog.get_logger(name)
