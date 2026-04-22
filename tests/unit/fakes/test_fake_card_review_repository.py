# ABOUTME: FakeCardReviewRepository contract tests — append-only list log.
# ABOUTME: Proves .saved is a list (not a dict); order matches insertion.
"""FakeCardReviewRepository unit tests."""

from __future__ import annotations

import uuid

from app.domain.entities import CardReview
from app.domain.value_objects import CardId, Rating
from tests.fakes.fake_card_review_repository import (
    FakeCardReviewRepository,
)


def _make_card_id() -> CardId:
    """Mint a fresh CardId for review tests."""
    return CardId(uuid.uuid4())


def test_save_appends_to_list() -> None:
    """Three save() calls produce three entries in insertion order."""
    repo = FakeCardReviewRepository()
    r1 = CardReview(card_id=_make_card_id(), rating=Rating.CORRECT)
    r2 = CardReview(card_id=_make_card_id(), rating=Rating.INCORRECT)
    r3 = CardReview(card_id=_make_card_id(), rating=Rating.CORRECT)
    repo.save(r1)
    repo.save(r2)
    repo.save(r3)
    assert repo.saved == [r1, r2, r3]


def test_saved_is_list_not_dict() -> None:
    """The public .saved attribute is a list of CardReview entries."""
    repo = FakeCardReviewRepository()
    assert isinstance(repo.saved, list)
    assert repo.saved == []
