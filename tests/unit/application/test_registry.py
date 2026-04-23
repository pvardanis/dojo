# ABOUTME: Tests for the generic Registry ABC in app.application.registry.
# ABOUTME: Uses an inline concrete subclass to exercise the abstract surface.
"""Registry ABC unit tests."""

from __future__ import annotations

import pytest

from app.application.registry import Registry
from app.domain.exceptions import DojoError


class _StubMissing(DojoError):
    """Missing-key error raised by the stub registry under test."""


class _StubRegistry(Registry[str, int]):
    """Minimal concrete Registry used to exercise the ABC."""

    def _missing_error(self, key: str) -> Exception:
        """Return a typed stub error naming the missing key."""
        return _StubMissing(f"missing {key!r}")


def test_registry_cannot_be_instantiated_directly() -> None:
    """The ABC refuses instantiation without a `_missing_error` impl."""
    with pytest.raises(TypeError, match="abstract"):
        Registry()  # type: ignore[abstract]


def test_get_returns_registered_value() -> None:
    """A key present in the entries mapping resolves to its value."""
    registry = _StubRegistry({"a": 1, "b": 2})

    assert registry.get("a") == 1
    assert registry.get("b") == 2


def test_get_missing_key_raises_subclass_domain_error() -> None:
    """An absent key triggers the subclass's `_missing_error` value."""
    registry = _StubRegistry({"a": 1})

    with pytest.raises(_StubMissing, match="missing 'z'"):
        registry.get("z")


def test_default_empty_registry_raises_for_any_key() -> None:
    """The default (empty) entries mapping fails every lookup."""
    registry = _StubRegistry()

    with pytest.raises(_StubMissing, match="missing 'anything'"):
        registry.get("anything")
