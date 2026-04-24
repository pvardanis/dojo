# ABOUTME: SQL adapter for the CardReviewRepository Protocol.
# ABOUTME: Append-only log; no `get` method per Protocol.
"""Sync SQL implementation of CardReviewRepository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.entities import CardReview
from app.infrastructure.db.mappers import card_review_to_row
from app.logging_config import get_logger

log = get_logger(__name__)


class SqlCardReviewRepository:
    """Sync SQL adapter for CardReviewRepository Protocol.

    Append-only persistent log of drill ratings; there is no `get` —
    the Protocol doesn't declare one.
    """

    def __init__(self, session: Session) -> None:
        """Hold the request-scoped session (CONTEXT D-01b).

        :param session: SQLAlchemy `Session` open for the caller's
            unit of work; the repo never commits or rolls back.
        """
        self._session = session

    def save(self, review: CardReview) -> None:
        """Append the review to the persistent log.

        :param review: The `CardReview` entry to append.
        """
        row = card_review_to_row(review)
        self._session.add(row)
        self._session.flush()
