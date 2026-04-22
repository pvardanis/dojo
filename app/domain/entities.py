# ABOUTME: Domain entities — Source, Note, Card, CardReview dataclasses.
# ABOUTME: Frozen, stdlib-only; IDs minted via default_factory at init.
"""Domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.value_objects import NoteId, SourceId, SourceKind


def _require_nonempty(value: str, field_name: str) -> None:
    """Raise ValueError if `value` is empty or whitespace-only."""
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


@dataclass(frozen=True)
class Source:
    """A source of study material."""

    kind: SourceKind
    user_prompt: str
    input: str | None = None
    id: SourceId = field(default_factory=lambda: SourceId(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Reject empty user_prompt after whitespace strip."""
        _require_nonempty(self.user_prompt, "user_prompt")


@dataclass(frozen=True)
class Note:
    """Generated note content linked to a Source."""

    source_id: SourceId
    content: str
    id: NoteId = field(default_factory=lambda: NoteId(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Reject empty content after whitespace strip."""
        _require_nonempty(self.content, "content")
