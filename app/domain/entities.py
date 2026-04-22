# ABOUTME: Domain entities — Source, Note, Card, CardReview dataclasses.
# ABOUTME: Frozen, stdlib-only; IDs minted via default_factory at init.
"""Domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.value_objects import (
    CardId,
    NoteId,
    Rating,
    ReviewId,
    SourceId,
    SourceKind,
)


def _require_nonempty(value: str, field_name: str) -> None:
    """Raise ValueError if `value` is empty or whitespace-only."""
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


@dataclass(frozen=True)
class Source:
    """Study-material source (TOPIC, FILE, or URL) with prompt + snapshot."""

    kind: SourceKind
    user_prompt: str
    display_name: str
    identifier: str | None = None
    source_text: str | None = None
    id: SourceId = field(default_factory=lambda: SourceId(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Enforce non-empty strings and kind/identifier coherence."""
        _require_nonempty(self.user_prompt, "user_prompt")
        _require_nonempty(self.display_name, "display_name")
        if self.kind is SourceKind.TOPIC:
            if self.identifier is not None:
                raise ValueError("TOPIC source must not carry identifier")
            if self.source_text is not None:
                raise ValueError("TOPIC source must not carry source_text")
        else:
            if self.identifier is None or not self.identifier.strip():
                raise ValueError(
                    f"{self.kind.value} source requires non-empty identifier"
                )
            if self.source_text is None or not self.source_text.strip():
                raise ValueError(
                    f"{self.kind.value} source requires non-empty source_text"
                )


@dataclass(frozen=True)
class Note:
    """LLM-generated note bound to a Source; overwritten on regenerate."""

    source_id: SourceId
    title: str
    content_md: str
    id: NoteId = field(default_factory=lambda: NoteId(uuid.uuid4()))
    generated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Reject empty title or content_md after whitespace strip."""
        _require_nonempty(self.title, "title")
        _require_nonempty(self.content_md, "content_md")


@dataclass(frozen=True)
class Card:
    """A single question-and-answer card linked to a Source."""

    source_id: SourceId
    question: str
    answer: str
    tags: tuple[str, ...] = ()
    id: CardId = field(default_factory=lambda: CardId(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Reject empty question or answer after whitespace strip."""
        _require_nonempty(self.question, "question")
        _require_nonempty(self.answer, "answer")


@dataclass(frozen=True)
class CardReview:
    """A single drill rating for one Card."""

    card_id: CardId
    rating: Rating
    id: ReviewId = field(default_factory=lambda: ReviewId(uuid.uuid4()))
    reviewed_at: datetime = field(default_factory=datetime.now)

    @property
    def is_correct(self) -> bool:
        """Derive the correct/incorrect boolean from the rating enum."""
        return self.rating is Rating.CORRECT
