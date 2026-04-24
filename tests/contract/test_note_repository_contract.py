# ABOUTME: TEST-03 contract harness — asserts NoteRepository shape.
# ABOUTME: Fake leg always runs; sql leg uses the session fixture.
"""NoteRepository contract tests — fake + sql impls."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.domain.entities import Note, Source
from app.domain.value_objects import NoteId, SourceId, SourceKind
from tests.fakes import FakeNoteRepository

_FIXED_SOURCE_ID = SourceId(uuid.uuid4())


@pytest.fixture(params=["fake", "sql"])
def note_repository(
    request: pytest.FixtureRequest,
    session: Session,
) -> Iterator:
    """Yield a fake or real NoteRepository."""
    if request.param == "fake":
        yield FakeNoteRepository()
        return
    from app.infrastructure.repositories.sql_note_repository import (
        SqlNoteRepository,
    )
    from app.infrastructure.repositories.sql_source_repository import (
        SqlSourceRepository,
    )

    # Seed the referenced Source so notes.source_id FK resolves
    # at flush time.
    SqlSourceRepository(session).save(
        Source(
            kind=SourceKind.TOPIC,
            user_prompt="p",
            display_name="d",
            id=_FIXED_SOURCE_ID,
        )
    )
    yield SqlNoteRepository(session)


def test_save_then_get_roundtrips(note_repository) -> None:
    """Saved Note is retrievable by id with every field preserved."""
    note = Note(
        source_id=_FIXED_SOURCE_ID,
        title="t",
        content_md="c",
    )
    note_repository.save(note)
    loaded = note_repository.get(note.id)
    assert loaded is not None
    assert loaded.id == note.id
    assert loaded.source_id == _FIXED_SOURCE_ID
    assert loaded.title == "t"
    assert loaded.content_md == "c"


def test_get_unknown_returns_none(note_repository) -> None:
    """Unknown id returns None, not a raise."""
    loaded = note_repository.get(NoteId(uuid.uuid4()))
    assert loaded is None
