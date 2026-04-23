# ABOUTME: Domain entities — Source, Note, Card, CardReview dataclasses.
# ABOUTME: Frozen, stdlib-only; validation lives at boundary layers.
"""Domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.value_objects import (
    CardId,
    NoteId,
    Rating,
    ReviewId,
    SourceId,
    SourceKind,
)


@dataclass(frozen=True)
class Source:
    """Study-material source (TOPIC, FILE, or URL) with prompt + snapshot."""

    kind: SourceKind
    user_prompt: str
    display_name: str
    identifier: str | None = None
    source_text: str | None = None
    id: SourceId = field(default_factory=lambda: SourceId(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class Note:
    """LLM-generated note bound to a Source; overwritten on regenerate."""

    source_id: SourceId
    title: str
    content_md: str
    id: NoteId = field(default_factory=lambda: NoteId(uuid.uuid4()))
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class Card:
    """A single question-and-answer card linked to a Source."""

    source_id: SourceId
    question: str
    answer: str
    tags: tuple[str, ...] = ()
    id: CardId = field(default_factory=lambda: CardId(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class CardReview:
    """A single drill rating for one Card."""

    card_id: CardId
    rating: Rating
    id: ReviewId = field(default_factory=lambda: ReviewId(uuid.uuid4()))
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_correct(self) -> bool:
        """Derive the correct/incorrect boolean from the rating enum.

        :returns: ``True`` when ``rating`` is ``Rating.CORRECT``; else
            ``False``.
        """
        return self.rating is Rating.CORRECT
