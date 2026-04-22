# ABOUTME: Unit tests for Card entity — structural + frozen semantics.
# ABOUTME: Validation lives at boundary layers; domain is pure data.
"""Unit tests for Card entity."""

from __future__ import annotations

import dataclasses
import uuid

import pytest

from app.domain.entities import Card
from app.domain.value_objects import SourceId


def _make_source_id() -> SourceId:
    """Mint a fresh SourceId for tests that need a parent reference."""
    return SourceId(uuid.uuid4())


def test_card_constructs_with_question_and_answer() -> None:
    """Card builds with question, answer, and a source_id."""
    card = Card(
        source_id=_make_source_id(),
        question="What is a Pod?",
        answer="The smallest deployable unit in Kubernetes.",
    )
    assert card.question == "What is a Pod?"
    assert card.answer.startswith("The smallest")


def test_card_default_tags_is_empty_tuple() -> None:
    """Card.tags defaults to () — hashable, frozen-safe."""
    card = Card(source_id=_make_source_id(), question="q?", answer="a.")
    assert card.tags == ()


def test_card_carries_source_id_association() -> None:
    """Card stores the SourceId it was constructed with."""
    sid = _make_source_id()
    card = Card(source_id=sid, question="q?", answer="a.")
    assert card.source_id is sid


def test_card_is_frozen() -> None:
    """Frozen dataclass: direct attribute assignment raises."""
    card = Card(source_id=_make_source_id(), question="q?", answer="a.")
    with pytest.raises(dataclasses.FrozenInstanceError):
        card.question = "new?"  # type: ignore[misc]
