# ABOUTME: Source entity invariants — non-empty prompt, unique IDs, frozen.
# ABOUTME: Exercises __post_init__ ValueError and frozen-dataclass semantics.
"""Source entity unit tests."""

from __future__ import annotations

import dataclasses

import pytest

from app.domain.entities import Source
from app.domain.value_objects import SourceKind


def test_source_construction_rejects_empty_user_prompt() -> None:
    """Source(user_prompt='') raises ValueError."""
    with pytest.raises(ValueError, match="non-empty"):
        Source(kind=SourceKind.TOPIC, user_prompt="")


def test_source_construction_rejects_whitespace_only_prompt() -> None:
    """Whitespace-only user_prompt is treated as empty."""
    with pytest.raises(ValueError, match="non-empty"):
        Source(kind=SourceKind.TOPIC, user_prompt="   \t\n  ")


def test_source_id_is_unique_per_instance() -> None:
    """Two Source() calls produce distinct SourceIds."""
    a = Source(kind=SourceKind.TOPIC, user_prompt="alpha")
    b = Source(kind=SourceKind.TOPIC, user_prompt="beta")
    assert a.id != b.id


def test_source_defaults_input_to_none() -> None:
    """Source.input defaults to None for the TOPIC kind."""
    s = Source(kind=SourceKind.TOPIC, user_prompt="alpha")
    assert s.input is None


def test_source_is_frozen() -> None:
    """Source is a frozen dataclass; attribute mutation raises."""
    s = Source(kind=SourceKind.TOPIC, user_prompt="alpha")
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.user_prompt = "beta"  # type: ignore[misc]
