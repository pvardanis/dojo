# ABOUTME: FakeNoteRepository contract tests — dict-by-id semantics.
# ABOUTME: Proves regenerate-overwrite via latest-wins dict upsert.
"""FakeNoteRepository unit tests."""

from __future__ import annotations

import uuid

from app.domain.entities import Note
from app.domain.value_objects import NoteId, SourceId
from tests.fakes.fake_note_repository import FakeNoteRepository


def _make_source_id() -> SourceId:
    """Mint a fresh SourceId for tests needing a parent reference."""
    return SourceId(uuid.uuid4())


def test_save_then_get_round_trips() -> None:
    """save then get by id returns the same Note."""
    repo = FakeNoteRepository()
    note = Note(source_id=_make_source_id(), title="t", content_md="body")
    repo.save(note)
    assert repo.get(note.id) == note


def test_get_missing_returns_none() -> None:
    """get on an unknown NoteId returns None."""
    repo = FakeNoteRepository()
    assert repo.get(NoteId(uuid.uuid4())) is None


def test_save_overwrites_by_note_id() -> None:
    """Saving twice with the same id keeps the latest entry."""
    repo = FakeNoteRepository()
    shared_id = NoteId(uuid.uuid4())
    sid = _make_source_id()
    first = Note(
        source_id=sid, title="old", content_md="old body", id=shared_id
    )
    second = Note(
        source_id=sid, title="new", content_md="new body", id=shared_id
    )
    repo.save(first)
    repo.save(second)
    assert len(repo.saved) == 1
    assert repo.saved[shared_id] is second
