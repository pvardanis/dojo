# ABOUTME: SQL adapter for the NoteRepository Protocol.
# ABOUTME: regenerate-overwrites via `session.merge` (CONTEXT D-02/D-07).
"""Sync SQL implementation of NoteRepository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.entities import Note
from app.domain.value_objects import NoteId
from app.infrastructure.db.mappers import note_from_row, note_to_row
from app.infrastructure.db.models import NoteRow
from app.logging_config import get_logger

log = get_logger(__name__)


class SqlNoteRepository:
    """Sync SQL adapter for NoteRepository Protocol.

    `save` is regenerate-overwrites (`session.merge`) — re-saving a Note
    with the same id replaces its columns in place.
    """

    def __init__(self, session: Session) -> None:
        """Hold the request-scoped session (CONTEXT D-01b).

        :param session: SQLAlchemy `Session` open for the caller's
            unit of work; the repo never commits or rolls back.
        """
        self._session = session

    def save(self, note: Note) -> None:
        """Upsert the note row, overwriting any existing row by id.

        :param note: The `Note` entity to persist.
        """
        row = note_to_row(note)
        self._session.merge(row)
        self._session.flush()

    def get(self, note_id: NoteId) -> Note | None:
        """Return the stored note or `None` if absent.

        :param note_id: Typed id of the note to load.
        :returns: The `Note` entity, or `None` when no row exists
            for `note_id`.
        """
        row = self._session.get(NoteRow, str(note_id))
        return note_from_row(row) if row is not None else None
