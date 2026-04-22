# ABOUTME: FakeCardRepository contract tests — dict-by-id semantics.
# ABOUTME: Append-only regeneration is a use-case concern, not the fake.
"""FakeCardRepository unit tests."""

from __future__ import annotations

import uuid

from app.domain.entities import Card
from app.domain.value_objects import CardId, SourceId
from tests.fakes.fake_card_repository import FakeCardRepository


def _make_source_id() -> SourceId:
    """Mint a fresh SourceId for tests needing a parent reference."""
    return SourceId(uuid.uuid4())


def test_save_then_get_round_trips() -> None:
    """save then get by id returns the same Card."""
    repo = FakeCardRepository()
    card = Card(source_id=_make_source_id(), question="q?", answer="a.")
    repo.save(card)
    assert repo.get(card.id) == card


def test_get_missing_returns_none() -> None:
    """get on an unknown CardId returns None."""
    repo = FakeCardRepository()
    assert repo.get(CardId(uuid.uuid4())) is None


def test_save_overwrites_same_card_id() -> None:
    """Saving twice with the same id keeps the latest entry."""
    repo = FakeCardRepository()
    shared_id = CardId(uuid.uuid4())
    sid = _make_source_id()
    first = Card(source_id=sid, question="q1?", answer="a1.", id=shared_id)
    second = Card(source_id=sid, question="q2?", answer="a2.", id=shared_id)
    repo.save(first)
    repo.save(second)
    assert len(repo.saved) == 1
    assert repo.saved[shared_id] is second
