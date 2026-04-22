# ABOUTME: Dict-backed fake CardRepository — exposes .saved state.
# ABOUTME: Append-only regeneration enforced at the use-case layer.
"""FakeCardRepository — dict-backed in-memory fake."""

from __future__ import annotations

from app.domain.entities import Card
from app.domain.value_objects import CardId


class FakeCardRepository:
    """In-memory dict of Card entities keyed by CardId."""

    def __init__(self) -> None:
        """Start with empty store."""
        self.saved: dict[CardId, Card] = {}

    def save(self, card: Card) -> None:
        """Insert or overwrite the card entry by id."""
        self.saved[card.id] = card

    def get(self, card_id: CardId) -> Card | None:
        """Return the stored card or None if missing."""
        return self.saved.get(card_id)
