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
    from app.application.dtos import (
        CardDTO,
        DraftBundle,
        GenerateRequest,
        NoteDTO,
    )


DraftToken = NewType("DraftToken", uuid.UUID)


class LLMProvider(Protocol):
    """Port for note + card generation via a language model."""

    def generate_note_and_cards(
        self,
        source_text: str | None,
        user_prompt: str,
    ) -> tuple[NoteDTO, list[CardDTO]]:
        """Generate a note + cards from source text and user prompt.

        :param source_text: Extracted source material; `None` for
            TOPIC requests where the prompt alone drives generation.
        :param user_prompt: Free-form user instruction appended to the
            provider's system prompt.
        :returns: A `(NoteDTO, [CardDTO, ...])` tuple; the card list
            is non-empty by DTO contract.
        :raises LLMOutputMalformed: If the provider's structured
            output fails DTO validation.
        """
        ...


class SourceRepository(Protocol):
    """Port for persisting and retrieving `Source` entities."""

    def save(self, source: Source) -> None:
        """Upsert the source row keyed by `source.id`.

        :param source: The `Source` entity to persist.
        """
        ...

    def get(self, source_id: SourceId) -> Source | None:
        """Return the stored source or `None` if absent.

        :param source_id: Typed id of the source to load.
        :returns: The `Source` entity, or `None` when no row
            exists for `source_id`.
        """
        ...


class NoteRepository(Protocol):
    """Port for persisting `Note` entities (regenerate-overwrites)."""

    def save(self, note: Note) -> None:
        """Upsert the note; adapters enforce regenerate-overwrite.

        :param note: The `Note` entity to persist; an existing row
            with the same id is replaced.
        """
        ...

    def get(self, note_id: NoteId) -> Note | None:
        """Return the stored note or `None` if absent.

        :param note_id: Typed id of the note to load.
        :returns: The `Note` entity, or `None` when no row exists
            for `note_id`.
        """
        ...


class CardRepository(Protocol):
    """Port for persisting `Card` entities (regenerate-appends)."""

    def save(self, card: Card) -> None:
        """Insert the card; adapters do not overwrite existing ids.

        :param card: The `Card` entity to persist.
        """
        ...

    def get(self, card_id: CardId) -> Card | None:
        """Return the stored card or `None` if absent.

        :param card_id: Typed id of the card to load.
        :returns: The `Card` entity, or `None` when no row exists
            for `card_id`.
        """
        ...


class CardReviewRepository(Protocol):
    """Port for the append-only `CardReview` log."""

    def save(self, review: CardReview) -> None:
        """Append the review to the persistent log.

        :param review: The `CardReview` entry to append.
        """
        ...


class DraftStore(Protocol):
    """In-memory holder for pending draft bundles (30-min TTL).

    Concurrency: put/pop are atomic in the adapter; pop is a
    read-and-delete. There is no `get` — callers commit-or-discard.
    """

    def put(self, token: DraftToken, bundle: DraftBundle) -> None:
        """Store the bundle under the token; TTL starts on write.

        :param token: The `DraftToken` minted for this pending
            draft.
        :param bundle: The `DraftBundle` to hold until a save or
            discard use case pops it.
        """
        ...

    def pop(self, token: DraftToken) -> DraftBundle | None:
        """Atomic read-and-delete; `None` if absent or expired.

        :param token: The `DraftToken` whose bundle to consume.
        :returns: The stored `DraftBundle`, or `None` when the
            token is unknown or its TTL has elapsed.
        """
        ...


# URL → text fetcher (stateless). Phase 3 trafilatura adapter.
type UrlFetcher = Callable[[str], str]

# Path → raw-text reader (stateless). Phase 3 filesystem adapter.
type SourceReader = Callable[[Path], str]

# GenerateRequest → extracted text. Keyed by SourceKind in the registry.
type SourceTextExtractor = Callable[[GenerateRequest], str]
