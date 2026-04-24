# ABOUTME: TEST-03 contract harness — asserts CardRepository shape.
# ABOUTME: Fake leg always runs; sql leg uses the session fixture.
"""CardRepository contract tests — fake + sql impls."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.domain.entities import Card, Source
from app.domain.value_objects import CardId, SourceId, SourceKind
from tests.fakes import FakeCardRepository

_FIXED_SOURCE_ID = SourceId(uuid.uuid4())


@pytest.fixture(params=["fake", "sql"])
def card_repository(
    request: pytest.FixtureRequest,
    session: Session,
) -> Iterator:
    """Yield a fake or real CardRepository."""
    if request.param == "fake":
        yield FakeCardRepository()
        return
    from app.infrastructure.repositories.sql_card_repository import (
        SqlCardRepository,
    )
    from app.infrastructure.repositories.sql_source_repository import (
        SqlSourceRepository,
    )

    # Seed a Source so FK constraint on cards.source_id resolves.
    SqlSourceRepository(session).save(
        Source(
            kind=SourceKind.TOPIC,
            user_prompt="p",
            display_name="d",
            id=_FIXED_SOURCE_ID,
        )
    )
    yield SqlCardRepository(session)


def test_save_then_get_roundtrips(card_repository) -> None:
    """Saved Card is retrievable by id with every field preserved."""
    card = Card(
        source_id=_FIXED_SOURCE_ID,
        question="q",
        answer="a",
    )
    card_repository.save(card)
    loaded = card_repository.get(card.id)
    assert loaded is not None
    assert loaded.id == card.id
    assert loaded.question == "q"
    assert loaded.answer == "a"
    assert loaded.tags == ()


def test_save_with_tags_roundtrips(card_repository) -> None:
    """tags tuple survives a save → get round trip."""
    card = Card(
        source_id=_FIXED_SOURCE_ID,
        question="q",
        answer="a",
        tags=("python", "sql"),
    )
    card_repository.save(card)
    loaded = card_repository.get(card.id)
    assert loaded is not None
    assert loaded.tags == ("python", "sql")


def test_get_unknown_returns_none(card_repository) -> None:
    """Unknown id returns None, not a raise."""
    loaded = card_repository.get(CardId(uuid.uuid4()))
    assert loaded is None
