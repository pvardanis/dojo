# ABOUTME: CardReview entity — rating + reviewed_at + is_correct property.
# ABOUTME: Exercises derived is_correct and frozen-dataclass semantics.
"""CardReview entity unit tests."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime

import pytest

from app.domain.entities import CardReview
from app.domain.value_objects import CardId, Rating


def _make_card_id() -> CardId:
    """Return a fresh CardId for test setup."""
    return CardId(uuid.uuid4())


def test_card_review_records_rating_and_time() -> None:
    """CardReview stores the rating and defaults reviewed_at to now()."""
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


def test_card_review_is_correct_raises_on_unknown_rating() -> None:
    """is_correct fails loud if a future Rating enum value is not handled."""
    review = CardReview(card_id=_make_card_id(), rating=Rating.CORRECT)
    # Bypass frozen/type-check to simulate a future enum member unmapped
    # in the match statement (e.g. Rating.SKIPPED if it lands later).
    object.__setattr__(review, "rating", "UNEXPECTED")
    with pytest.raises(ValueError, match="unhandled Rating"):
        _ = review.is_correct


def test_card_review_carries_card_id_association() -> None:
    """CardReview stores the card_id it was constructed with."""
    cid = _make_card_id()
    review = CardReview(card_id=cid, rating=Rating.CORRECT)
    assert review.card_id == cid


def test_card_review_is_frozen() -> None:
    """CardReview is a frozen dataclass; attribute mutation raises."""
    review = CardReview(card_id=_make_card_id(), rating=Rating.CORRECT)
    with pytest.raises(dataclasses.FrozenInstanceError):
        review.rating = Rating.INCORRECT  # type: ignore[misc]


def test_card_review_rejects_naive_reviewed_at() -> None:
    """CardReview with a naive datetime raises ValueError."""
    with pytest.raises(ValueError, match="reviewed_at must be timezone-aware"):
        CardReview(
            card_id=_make_card_id(),
            rating=Rating.CORRECT,
            reviewed_at=datetime(2026, 4, 22, 9, 0, 0),
        )
