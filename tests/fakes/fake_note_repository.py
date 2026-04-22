# ABOUTME: Dict-backed fake NoteRepository — exposes .saved state.
# ABOUTME: Regenerate-overwrite is the natural dict-upsert semantic.
"""FakeNoteRepository — dict-backed in-memory fake."""

from __future__ import annotations

from app.domain.entities import Note
from app.domain.value_objects import NoteId


class FakeNoteRepository:
    """In-memory dict of Note entities keyed by NoteId."""

    def __init__(self) -> None:
        """Start with empty store."""
        self.saved: dict[NoteId, Note] = {}

    def save(self, note: Note) -> None:
        """Insert or overwrite the note entry (regenerate-overwrites)."""
        self.saved[note.id] = note

    def get(self, note_id: NoteId) -> Note | None:
        """Return the stored note or None if missing."""
        return self.saved.get(note_id)
