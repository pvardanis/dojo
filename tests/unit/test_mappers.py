# ABOUTME: Unit tests — mapper round-trip, no DB, pure functions.
# ABOUTME: Catches UUID↔str, enum↔str, tags JSON drift.
"""Pure-function mapper round-trip tests (PERSIST-02)."""

from __future__ import annotations

import uuid

from app.domain.entities import Card, CardReview, Note, Source
from app.domain.value_objects import (
    CardId,
    Rating,
    SourceId,
    SourceKind,
)
from app.infrastructure.db.mappers import (
    card_from_row,
    card_review_from_row,
    card_review_to_row,
    card_to_row,
    note_from_row,
    note_to_row,
    source_from_row,
    source_to_row,
)


def test_source_round_trip() -> None:
    """Source → row → Source preserves every field."""
    src = Source(
        kind=SourceKind.TOPIC,
        user_prompt="p",
        display_name="d",
    )
    assert source_from_row(source_to_row(src)) == src


def test_source_file_kind_round_trips() -> None:
    """FILE kind survives .value↔Enum conversion."""
    src = Source(
        kind=SourceKind.FILE,
        user_prompt="p",
        display_name="d",
        identifier="/tmp/x.md",
        source_text="hello",
    )
    assert source_from_row(source_to_row(src)) == src


def test_note_round_trip() -> None:
    """Note → row → Note preserves source_id UUID and generated_at."""
    note = Note(
        source_id=SourceId(uuid.uuid4()),
        title="t",
        content_md="c",
    )
    assert note_from_row(note_to_row(note)) == note


def test_card_round_trip_with_tags() -> None:
    """Card tags tuple survives JSON round-trip."""
    card = Card(
        source_id=SourceId(uuid.uuid4()),
        question="q",
        answer="a",
        tags=("python", "sql"),
    )
    assert card_from_row(card_to_row(card)) == card


def test_card_round_trip_empty_tags() -> None:
    """Empty tags tuple stored as '[]' reads back as ()."""
    card = Card(
        source_id=SourceId(uuid.uuid4()),
        question="q",
        answer="a",
    )
    roundtripped = card_from_row(card_to_row(card))
    assert roundtripped.tags == ()
    assert roundtripped == card


def test_card_review_round_trip() -> None:
    """CardReview rating survives Rating.value↔Rating."""
    review = CardReview(
        card_id=CardId(uuid.uuid4()),
        rating=Rating.CORRECT,
    )
    roundtripped = card_review_from_row(card_review_to_row(review))
    assert roundtripped == review
    assert roundtripped.is_correct is True
