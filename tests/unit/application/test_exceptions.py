# ABOUTME: Application-layer exception hierarchy tests.
# ABOUTME: Every exception inherits from DojoError; messages round-trip.
"""Application exception tests."""

from __future__ import annotations

import pytest

from app.application.exceptions import (
    DraftExpired,
    LLMOutputMalformed,
    UnsupportedSourceKind,
)
from app.domain.exceptions import DojoError


def test_unsupported_source_kind_inherits_dojo_error() -> None:
    """UnsupportedSourceKind is a DojoError subclass."""
    assert issubclass(UnsupportedSourceKind, DojoError)


def test_draft_expired_inherits_dojo_error() -> None:
    """DraftExpired is a DojoError subclass."""
    assert issubclass(DraftExpired, DojoError)


def test_llm_output_malformed_inherits_dojo_error() -> None:
    """LLMOutputMalformed is a DojoError subclass."""
    assert issubclass(LLMOutputMalformed, DojoError)


def test_application_exception_carries_message() -> None:
    """Raising UnsupportedSourceKind preserves its message via str()."""
    with pytest.raises(UnsupportedSourceKind) as exc_info:
        raise UnsupportedSourceKind("x")
    assert str(exc_info.value) == "x"
