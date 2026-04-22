# ABOUTME: Card entity invariants — non-empty Q&A, default tags, frozen.
# ABOUTME: Exercises __post_init__ for question and answer fields.
"""Card entity unit tests."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime

import pytest

from app.domain.entities import Card
from app.domain.value_objects import SourceId


def _make_source_id() -> SourceId:
    """Return a fresh SourceId for test setup."""
    return SourceId(uuid.uuid4())


def test_card_rejects_empty_question() -> None:
    """Card(question='') raises ValueError mentioning the field."""
    with pytest.raises(ValueError, match="question"):
        Card(source_id=_make_source_id(), question="", answer="a.")


def test_card_rejects_empty_answer() -> None:
    """Card(answer='') raises ValueError mentioning the field."""
    with pytest.raises(ValueError, match="answer"):
        Card(source_id=_make_source_id(), question="q?", answer="")


def test_card_default_tags_is_empty_tuple() -> None:
    """Card.tags defaults to () — empty tuple, hashable and frozen-safe."""
    card = Card(source_id=_make_source_id(), question="q?", answer="a.")
    assert card.tags == ()


def test_card_carries_source_id_association() -> None:
    """Card stores the source_id it was constructed with."""
    sid = _make_source_id()
    card = Card(source_id=sid, question="q?", answer="a.")
    assert card.source_id == sid


def test_card_is_frozen() -> None:
    """Card is a frozen dataclass; attribute mutation raises."""
    card = Card(source_id=_make_source_id(), question="q?", answer="a.")
    with pytest.raises(dataclasses.FrozenInstanceError):
        card.question = "new?"  # type: ignore[misc]


def test_card_equality_and_hash() -> None:
    """Two freshly-constructed Cards are NOT equal (distinct ids); hashable."""
    sid = _make_source_id()
    a = Card(source_id=sid, question="q?", answer="a.")
    b = Card(source_id=sid, question="q?", answer="a.")
    assert a != b
    assert a == a
    assert {a, a} == {a}


def test_card_rejects_empty_tag() -> None:
    """Empty/whitespace-only tag entries raise ValueError."""
    with pytest.raises(ValueError, match=r"tags\[1\] must be non-empty"):
        Card(
            source_id=_make_source_id(),
            question="q?",
            answer="a.",
            tags=("python", "  "),
        )


def test_card_rejects_duplicate_tags() -> None:
    """Duplicate tag entries raise ValueError."""
    with pytest.raises(ValueError, match="tags must not contain duplicates"):
        Card(
            source_id=_make_source_id(),
            question="q?",
            answer="a.",
            tags=("python", "python"),
        )


def test_card_accepts_multiple_distinct_tags() -> None:
    """A tuple of distinct, non-empty tags is accepted verbatim."""
    card = Card(
        source_id=_make_source_id(),
        question="q?",
        answer="a.",
        tags=("python", "kubernetes", "helm"),
    )
    assert card.tags == ("python", "kubernetes", "helm")


def test_card_rejects_naive_created_at() -> None:
    """Card construction with a naive datetime raises ValueError."""
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        Card(
            source_id=_make_source_id(),
            question="q?",
            answer="a.",
            created_at=datetime(2026, 4, 22, 9, 0, 0),
        )
