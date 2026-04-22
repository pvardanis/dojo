# ABOUTME: Application ports — Protocols, Callable aliases, NewTypes.
# ABOUTME: Structural subtyping; no @runtime_checkable (zero runtime cost).
"""Application layer ports (DIP boundary)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, NewType, Protocol

from app.domain.entities import Card, CardReview, Note, Source
from app.domain.value_objects import CardId, NoteId, SourceId

if TYPE_CHECKING:
    from app.application.dtos import CardDTO, DraftBundle, NoteDTO


DraftToken = NewType("DraftToken", uuid.UUID)


class LLMProvider(Protocol):
    """Port for note + card generation via a language model."""

    def generate_note_and_cards(
        self,
        source_text: str | None,
        user_prompt: str,
    ) -> tuple[NoteDTO, list[CardDTO]]:
        """Generate a note + cards; raise LLMOutputMalformed on bad shape."""
        ...


class SourceRepository(Protocol):
    """Port for persisting and retrieving `Source` entities."""

    def save(self, source: Source) -> None:
        """Upsert the source row keyed by `source.id`."""
        ...

    def get(self, source_id: SourceId) -> Source | None:
        """Return the stored source or None if absent."""
        ...


class NoteRepository(Protocol):
    """Port for persisting `Note` entities (regenerate-overwrites)."""

    def save(self, note: Note) -> None:
        """Upsert; regenerate-overwrite semantics enforced by adapter."""
        ...

    def get(self, note_id: NoteId) -> Note | None:
        """Return the stored note or None if absent."""
        ...


class CardRepository(Protocol):
    """Port for persisting `Card` entities (regenerate-appends)."""

    def save(self, card: Card) -> None:
        """Insert the card; adapters do not overwrite existing ids."""
        ...

    def get(self, card_id: CardId) -> Card | None:
        """Return the stored card or None if absent."""
        ...


class CardReviewRepository(Protocol):
    """Port for the append-only `CardReview` log."""

    def save(self, review: CardReview) -> None:
        """Append the review to the persistent log."""
        ...


class DraftStore(Protocol):
    """In-memory holder for pending draft bundles (30-min TTL).

    Concurrency: put/pop are atomic in the adapter; pop is a
    read-and-delete. There is no `get` — callers commit-or-discard.
    """

    def put(self, token: DraftToken, bundle: DraftBundle) -> None:
        """Store the bundle under the token; TTL starts on write."""
        ...

    def pop(self, token: DraftToken) -> DraftBundle | None:
        """Atomic read-and-delete; None if absent or expired."""
        ...


# URL → text fetcher (stateless). Phase 3 trafilatura adapter.
type UrlFetcher = Callable[[str], str]

# Path → raw-text reader (stateless). Phase 3 filesystem adapter.
type SourceReader = Callable[[Path], str]
