# ABOUTME: Pure mapper functions — domain dataclass ↔ ORM row class.
# ABOUTME: Unit-testable without a DB fixture; no classes, no state.
"""Mappers between domain entities and SQLAlchemy row classes."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

from app.application.exceptions import RepositoryRowCorrupt
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


def _parse_or_corrupt[T](
    table: str,
    row_id: str,
    field: str,
    value: str,
    parser: Callable[[str], T],
) -> T:
    """Run `parser(value)`, wrapping stdlib errors as DojoError.

    Centralises the stdlib-exception→`RepositoryRowCorrupt` translation
    so repository callers see one `DojoError` subclass instead of a
    raw `ValueError` / `JSONDecodeError` leaking through the
    persistence boundary.

    :param table: SQL table name, forwarded to the exception.
    :param row_id: Primary key of the offending row.
    :param field: Column name being parsed.
    :param value: Raw column value.
    :param parser: Callable that converts the raw string into a
        domain value (`uuid.UUID`, an Enum class, `json.loads`, ...).
    :returns: The parsed domain value.
    :raises RepositoryRowCorrupt: When the parser raises `ValueError`
        or `json.JSONDecodeError`.
    """
    try:
        return parser(value)
    except (ValueError, json.JSONDecodeError) as err:
        raise RepositoryRowCorrupt(
            table=table,
            row_id=row_id,
            field=field,
            value=str(value),
        ) from err


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
        id=SourceId(
            _parse_or_corrupt("sources", row.id, "id", row.id, uuid.UUID)
        ),
        kind=_parse_or_corrupt(
            "sources", row.id, "kind", row.kind, SourceKind
        ),
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
        id=NoteId(_parse_or_corrupt("notes", row.id, "id", row.id, uuid.UUID)),
        source_id=SourceId(
            _parse_or_corrupt(
                "notes", row.id, "source_id", row.source_id, uuid.UUID
            )
        ),
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
    tags_raw = _parse_or_corrupt("cards", row.id, "tags", row.tags, json.loads)
    if not isinstance(tags_raw, list):
        raise RepositoryRowCorrupt(
            table="cards",
            row_id=row.id,
            field="tags",
            value=str(row.tags),
        )
    return Card(
        id=CardId(_parse_or_corrupt("cards", row.id, "id", row.id, uuid.UUID)),
        source_id=SourceId(
            _parse_or_corrupt(
                "cards", row.id, "source_id", row.source_id, uuid.UUID
            )
        ),
        question=row.question,
        answer=row.answer,
        tags=tuple(tags_raw),
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
        id=ReviewId(
            _parse_or_corrupt("card_reviews", row.id, "id", row.id, uuid.UUID)
        ),
        card_id=CardId(
            _parse_or_corrupt(
                "card_reviews",
                row.id,
                "card_id",
                row.card_id,
                uuid.UUID,
            )
        ),
        rating=_parse_or_corrupt(
            "card_reviews", row.id, "rating", row.rating, Rating
        ),
        reviewed_at=row.reviewed_at,
    )
