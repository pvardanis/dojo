# ABOUTME: FakeSourceRepository contract tests — dict-by-id semantics.
# ABOUTME: Proves .saved exposes state assertable by round-trip tests.
"""FakeSourceRepository unit tests."""

from __future__ import annotations

import uuid

from app.domain.entities import Source
from app.domain.value_objects import SourceId, SourceKind
from tests.fakes.fake_source_repository import FakeSourceRepository


def _make_source(user_prompt: str = "p") -> Source:
    """Build a TOPIC source with a stable display name for tests."""
    return Source(
        kind=SourceKind.TOPIC,
        user_prompt=user_prompt,
        display_name="test topic",
    )


def test_save_then_get_round_trips() -> None:
    """save then get by id returns the same Source."""
    repo = FakeSourceRepository()
    src = _make_source()
    repo.save(src)
    assert repo.get(src.id) == src


def test_get_missing_returns_none() -> None:
    """get on an unknown SourceId returns None."""
    repo = FakeSourceRepository()
    assert repo.get(SourceId(uuid.uuid4())) is None


def test_saved_dict_exposes_state() -> None:
    """Public .saved dict holds the saved source keyed by its id."""
    repo = FakeSourceRepository()
    src = _make_source()
    repo.save(src)
    assert repo.saved[src.id] is src


def test_save_overwrites_same_id() -> None:
    """Saving twice with the same id keeps a single latest entry."""
    repo = FakeSourceRepository()
    shared_id = SourceId(uuid.uuid4())
    first = Source(
        kind=SourceKind.TOPIC,
        user_prompt="first",
        display_name="t",
        id=shared_id,
    )
    second = Source(
        kind=SourceKind.TOPIC,
        user_prompt="second",
        display_name="t",
        id=shared_id,
    )
    repo.save(first)
    repo.save(second)
    assert len(repo.saved) == 1
    assert repo.saved[shared_id] is second
