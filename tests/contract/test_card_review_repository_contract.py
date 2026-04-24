# ABOUTME: TEST-03 contract harness — CardReviewRepository.
# ABOUTME: Append-only port; no get() method (matches Protocol).
"""CardReviewRepository contract tests — fake + sql impls."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.domain.entities import Card, CardReview, Source
from app.domain.value_objects import CardId, Rating, SourceId, SourceKind
from tests.fakes import FakeCardReviewRepository

_FIXED_SOURCE_ID = SourceId(uuid.uuid4())
_FIXED_CARD_ID = CardId(uuid.uuid4())


@pytest.fixture(params=["fake", "sql"])
def card_review_repository(
    request: pytest.FixtureRequest,
    session: Session,
) -> Iterator:
    """Yield a fake or real CardReviewRepository."""
    if request.param == "fake":
        yield FakeCardReviewRepository()
        return
    from app.infrastructure.repositories.sql_card_repository import (
        SqlCardRepository,
    )
    from app.infrastructure.repositories.sql_card_review_repository import (
        SqlCardReviewRepository,
    )
    from app.infrastructure.repositories.sql_source_repository import (
        SqlSourceRepository,
    )

    # Seed Source + Card so the FK on card_reviews.card_id resolves.
    SqlSourceRepository(session).save(
        Source(
            kind=SourceKind.TOPIC,
            user_prompt="p",
            display_name="d",
            id=_FIXED_SOURCE_ID,
        )
    )
    SqlCardRepository(session).save(
        Card(
            source_id=_FIXED_SOURCE_ID,
            question="q",
            answer="a",
            id=_FIXED_CARD_ID,
        )
    )
    yield SqlCardReviewRepository(session)


def test_save_two_reviews_does_not_raise(card_review_repository) -> None:
    """Append-only log accepts multiple saves without error."""
    card_review_repository.save(
        CardReview(card_id=_FIXED_CARD_ID, rating=Rating.CORRECT)
    )
    card_review_repository.save(
        CardReview(card_id=_FIXED_CARD_ID, rating=Rating.INCORRECT)
    )
