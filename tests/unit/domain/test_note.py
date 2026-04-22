# ABOUTME: Note entity invariants — non-empty content, source association.
# ABOUTME: Exercises __post_init__ ValueError and NoteId uniqueness.
"""Note entity unit tests."""

from __future__ import annotations

import dataclasses
import uuid

import pytest

from app.domain.entities import Note
from app.domain.value_objects import SourceId


def _make_source_id() -> SourceId:
    """Return a fresh SourceId for test setup."""
    return SourceId(uuid.uuid4())


def test_note_construction_rejects_empty_content() -> None:
    """Note(content='') raises ValueError."""
    with pytest.raises(ValueError, match="non-empty"):
        Note(source_id=_make_source_id(), content="")


def test_note_carries_source_id_association() -> None:
    """Note stores the source_id it was constructed with."""
    sid = _make_source_id()
    note = Note(source_id=sid, content="hello")
    assert note.source_id == sid


def test_note_id_is_unique() -> None:
    """Two Note() calls produce distinct NoteIds."""
    sid = _make_source_id()
    a = Note(source_id=sid, content="alpha")
    b = Note(source_id=sid, content="beta")
    assert a.id != b.id


def test_note_is_frozen() -> None:
    """Note is a frozen dataclass; attribute mutation raises."""
    note = Note(source_id=_make_source_id(), content="hello")
    with pytest.raises(dataclasses.FrozenInstanceError):
        note.content = "world"  # type: ignore[misc]
