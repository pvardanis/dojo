# ABOUTME: Unit-test-only fixtures.
# ABOUTME: Clamp Dojo's own loggers to WARNING for pristine output.
"""Unit-test-only fixture overrides."""

from __future__ import annotations

import logging

import pytest


@pytest.fixture(scope="session", autouse=True)
def _clamp_dojo_loggers() -> None:
    """Set Dojo's own loggers to WARNING during unit tests.

    Unit tests should not produce any log output unless the test
    itself is asserting on a log line. Session-scoped clamp runs
    once per pytest process.
    """
    for name in ("dojo", "app"):
        logging.getLogger(name).setLevel(logging.WARNING)
