# ABOUTME: OPS-04 gate — structlog configure + get_logger smoke.
# ABOUTME: Confirms logging pipeline does not raise at runtime.
"""Structured logging smoke test."""

from __future__ import annotations

from app.logging_config import configure_logging, get_logger


def test_configure_logging_and_log_event_do_not_raise() -> None:
    """`configure_logging` + `get_logger(x).info(...)` is safe.

    pristine-output rule (filterwarnings=error) catches any
    structlog misconfig at runtime. Test passes if the call
    sequence does not raise.
    """
    configure_logging("INFO")
    log = get_logger("dojo.test")
    log.info("smoke", key="value")
