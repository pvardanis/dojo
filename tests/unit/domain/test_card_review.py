# ABOUTME: Unit tests for CardReview entity — rating + is_correct property.
# ABOUTME: Validation lives at boundary layers; domain is pure data.
"""Unit tests for CardReview entity."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime

import pytest

from app.domain.entities import CardReview
from app.domain.value_objects import CardId, Rating


def _make_card_id() -> CardId:
    """Mint a fresh CardId for tests that need a parent reference."""
    return CardId(uuid.uuid4())


def test_card_review_records_rating_and_time() -> None:
    """CardReview stores the rating and reviewed_at defaults to now."""
    cid = _make_card_id()
    review = CardReview(card_id=cid, rating=Rating.CORRECT)
    assert review.rating is Rating.CORRECT
    assert isinstance(review.reviewed_at, datetime)


def test_card_review_is_correct_matches_rating() -> None:
    """is_correct is True for CORRECT, False for INCORRECT."""
    cid = _make_card_id()
    correct = CardReview(card_id=cid, rating=Rating.CORRECT)
    incorrect = CardReview(card_id=cid, rating=Rating.INCORRECT)
    assert correct.is_correct is True
    assert incorrect.is_correct is False


def test_card_review_is_correct_is_a_property_not_a_field() -> None:
    """is_correct is a derived @property, not a stored dataclass field.

    Pins the architectural choice (derived, not stored) against a
    future refactor that adds `is_correct: bool = field(...)` —
    which would reopen the stored-vs-computed drift risk.
    """
    field_names = {f.name for f in dataclasses.fields(CardReview)}
    assert "is_correct" not in field_names
    assert isinstance(CardReview.is_correct, property)


def test_card_review_carries_card_id_association() -> None:
    """CardReview stores the CardId it was constructed with."""
    cid = _make_card_id()
    review = CardReview(card_id=cid, rating=Rating.CORRECT)
    assert review.card_id is cid


def test_card_review_is_frozen() -> None:
    """Frozen dataclass: direct attribute assignment raises."""
    review = CardReview(card_id=_make_card_id(), rating=Rating.CORRECT)
    with pytest.raises(dataclasses.FrozenInstanceError):
        review.rating = Rating.INCORRECT  # type: ignore[misc]
