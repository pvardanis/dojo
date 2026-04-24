# ABOUTME: SQL adapter for the CardRepository Protocol.
# ABOUTME: regenerate-appends via `session.add` — never merge (PERSIST-02).
"""Sync SQL implementation of CardRepository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.entities import Card
from app.domain.value_objects import CardId
from app.infrastructure.db.mappers import card_from_row, card_to_row
from app.infrastructure.db.models import CardRow
from app.logging_config import get_logger

log = get_logger(__name__)


class SqlCardRepository:
    """Sync SQL adapter for CardRepository Protocol.

    `save` is regenerate-appends (`session.add`) — never overwrites by
    id. Card regeneration accumulates new rows; PERSIST-02.
    """

    def __init__(self, session: Session) -> None:
        """Hold the request-scoped session (CONTEXT D-01b).

        :param session: SQLAlchemy `Session` open for the caller's
            unit of work; the repo never commits or rolls back.
        """
        self._session = session

    def save(self, card: Card) -> None:
        """Insert the card; never overwrites by id (PERSIST-02).

        :param card: The `Card` entity to persist.
        """
        row = card_to_row(card)
        self._session.add(row)
        self._session.flush()

    def get(self, card_id: CardId) -> Card | None:
        """Return the stored card or `None` if absent.

        :param card_id: Typed id of the card to load.
        :returns: The `Card` entity, or `None` when no row exists
            for `card_id`.
        """
        row = self._session.get(CardRow, str(card_id))
        return card_from_row(row) if row is not None else None
