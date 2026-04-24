# ABOUTME: Pure mapper functions — domain dataclass ↔ ORM row class.
# ABOUTME: Unit-testable without a DB fixture; no classes, no state.
"""Mappers between domain entities and SQLAlchemy row classes."""

from __future__ import annotations

import json
import uuid

from app.domain.entities import Card, CardReview, Note, Source
from app.domain.value_objects import (
    CardId,
    NoteId,
    Rating,
    ReviewId,
    SourceId,
    SourceKind,
)
from app.infrastructure.db.models import (
    CardReviewRow,
    CardRow,
    NoteRow,
    SourceRow,
)


def source_to_row(src: Source) -> SourceRow:
    """Convert a `Source` domain entity to a `SourceRow`."""
    return SourceRow(
        id=str(src.id),
        kind=src.kind.value,
        user_prompt=src.user_prompt,
        display_name=src.display_name,
        identifier=src.identifier,
        source_text=src.source_text,
        created_at=src.created_at,
    )


def source_from_row(row: SourceRow) -> Source:
    """Convert a `SourceRow` back to a `Source` domain entity."""
    return Source(
        id=SourceId(uuid.UUID(row.id)),
        kind=SourceKind(row.kind),
        user_prompt=row.user_prompt,
        display_name=row.display_name,
        identifier=row.identifier,
        source_text=row.source_text,
        created_at=row.created_at,
    )


def note_to_row(note: Note) -> NoteRow:
    """Convert a `Note` domain entity to a `NoteRow`."""
    return NoteRow(
        id=str(note.id),
        source_id=str(note.source_id),
        title=note.title,
        content_md=note.content_md,
        generated_at=note.generated_at,
    )


def note_from_row(row: NoteRow) -> Note:
    """Convert a `NoteRow` back to a `Note` domain entity."""
    return Note(
        id=NoteId(uuid.UUID(row.id)),
        source_id=SourceId(uuid.UUID(row.source_id)),
        title=row.title,
        content_md=row.content_md,
        generated_at=row.generated_at,
    )


def card_to_row(card: Card) -> CardRow:
    """Convert a `Card` domain entity to a `CardRow`."""
    return CardRow(
        id=str(card.id),
        source_id=str(card.source_id),
        question=card.question,
        answer=card.answer,
        tags=json.dumps(list(card.tags)),
        created_at=card.created_at,
    )


def card_from_row(row: CardRow) -> Card:
    """Convert a `CardRow` back to a `Card` domain entity."""
    return Card(
        id=CardId(uuid.UUID(row.id)),
        source_id=SourceId(uuid.UUID(row.source_id)),
        question=row.question,
        answer=row.answer,
        tags=tuple(json.loads(row.tags)),
        created_at=row.created_at,
    )


def card_review_to_row(review: CardReview) -> CardReviewRow:
    """Convert a `CardReview` domain entity to a `CardReviewRow`."""
    return CardReviewRow(
        id=str(review.id),
        card_id=str(review.card_id),
        rating=review.rating.value,
        reviewed_at=review.reviewed_at,
    )


def card_review_from_row(row: CardReviewRow) -> CardReview:
    """Convert a `CardReviewRow` back to a `CardReview` entity."""
    return CardReview(
        id=ReviewId(uuid.UUID(row.id)),
        card_id=CardId(uuid.UUID(row.card_id)),
        rating=Rating(row.rating),
        reviewed_at=row.reviewed_at,
    )
