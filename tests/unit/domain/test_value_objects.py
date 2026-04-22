# ABOUTME: Value-object smoke tests — SourceKind, Rating, typed IDs.
# ABOUTME: Enum membership + NewType-UUID zero-cost assertion.
"""Value-object unit tests."""

from __future__ import annotations

import uuid

from app.domain.value_objects import (
    CardId,
    NoteId,
    Rating,
    ReviewId,
    SourceId,
    SourceKind,
)


def test_source_kind_members() -> None:
    """SourceKind contains exactly FILE, URL, TOPIC."""
    assert {m.name for m in SourceKind} == {"FILE", "URL", "TOPIC"}


def test_rating_members() -> None:
    """Rating contains exactly CORRECT, INCORRECT."""
    assert {m.name for m in Rating} == {"CORRECT", "INCORRECT"}


def test_new_type_ids_wrap_uuid() -> None:
    """Each typed ID is importable and wraps a runtime uuid.UUID."""
    raw = uuid.uuid4()
    source_id = SourceId(raw)
    note_id = NoteId(raw)
    card_id = CardId(raw)
    review_id = ReviewId(raw)
    assert isinstance(source_id, uuid.UUID)
    assert isinstance(note_id, uuid.UUID)
    assert isinstance(card_id, uuid.UUID)
    assert isinstance(review_id, uuid.UUID)


def test_new_type_ids_are_distinct_at_type_level() -> None:
    """The 4 ID NewTypes are distinct constructors over uuid.UUID.

    This is the load-bearing guarantee of D-01: a refactor collapsing
    `SourceId = NoteId = uuid.UUID` would silently break every repo
    and use-case that relies on the distinction. The test pins the
    distinction against future drift.
    """
    assert SourceId is not NoteId
    assert NoteId is not CardId
    assert CardId is not ReviewId
    assert SourceId is not ReviewId
    assert SourceId.__supertype__ is uuid.UUID
    assert NoteId.__supertype__ is uuid.UUID
    assert CardId.__supertype__ is uuid.UUID
    assert ReviewId.__supertype__ is uuid.UUID
