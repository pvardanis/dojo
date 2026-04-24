# ABOUTME: SQL adapter for the SourceRepository Protocol.
# ABOUTME: Thin glue: mapper + session.merge / session.get.
"""Sync SQL implementation of SourceRepository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.entities import Source
from app.domain.value_objects import SourceId
from app.infrastructure.db.mappers import (
    source_from_row,
    source_to_row,
)
from app.infrastructure.db.models import SourceRow
from app.logging_config import get_logger

log = get_logger(__name__)


class SqlSourceRepository:
    """Sync SQL adapter for SourceRepository Protocol."""

    def __init__(self, session: Session) -> None:
        """Hold the request-scoped session (CONTEXT D-01b).

        :param session: SQLAlchemy `Session` open for the caller's
            unit of work; the repo never commits or rolls back.
        """
        self._session = session

    def save(self, source: Source) -> None:
        """Upsert the source row keyed by `source.id`.

        :param source: The `Source` entity to persist.
        """
        row = source_to_row(source)
        self._session.merge(row)
        self._session.flush()

    def get(self, source_id: SourceId) -> Source | None:
        """Return the stored source or `None` if absent.

        :param source_id: Typed id of the source to load.
        :returns: The `Source` entity, or `None` when no row exists
            for `source_id`.
        """
        row = self._session.get(SourceRow, str(source_id))
        return source_from_row(row) if row is not None else None
