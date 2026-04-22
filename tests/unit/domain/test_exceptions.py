# ABOUTME: DojoError smoke test — hierarchy base class assertions.
# ABOUTME: Establishes the root of the domain exception tree.
"""Domain exceptions unit tests."""

from __future__ import annotations

import pytest

from app.domain.exceptions import DojoError


def test_dojo_error_is_exception() -> None:
    """DojoError subclasses Exception and round-trips its message."""
    assert issubclass(DojoError, Exception)
    with pytest.raises(DojoError) as info:
        raise DojoError("boom")
    assert str(info.value) == "boom"
