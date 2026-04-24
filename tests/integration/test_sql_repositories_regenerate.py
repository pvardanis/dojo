# ABOUTME: SC #7 — regenerate overwrites Note, appends Cards.
# ABOUTME: PERSIST-02 (spec §4.3): notes upsert, cards accumulate.
"""Regenerate semantics — SC #7 (Note overwrite + Card append)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Card, Note, Source
from app.domain.value_objects import NoteId, SourceKind
from app.infrastructure.db.models import CardRow
from app.infrastructure.repositories.sql_card_repository import (
    SqlCardRepository,
)
from app.infrastructure.repositories.sql_note_repository import (
    SqlNoteRepository,
)
from app.infrastructure.repositories.sql_source_repository import (
    SqlSourceRepository,
)


def test_regenerate_note_overwrites_same_id(session: Session) -> None:
    """Saving a Note with an existing id replaces title/content."""
    src_repo = SqlSourceRepository(session)
    note_repo = SqlNoteRepository(session)

    src = Source(
        kind=SourceKind.TOPIC,
        user_prompt="p",
        display_name="d",
    )
    src_repo.save(src)

    fixed_id = NoteId(uuid.uuid4())
    v1 = Note(
        id=fixed_id,
        source_id=src.id,
        title="t1",
        content_md="c1",
    )
    note_repo.save(v1)
    first = note_repo.get(fixed_id)
    assert first is not None
    assert first.title == "t1"

    v2 = Note(
        id=fixed_id,
        source_id=src.id,
        title="t2",
        content_md="c2",
    )
    note_repo.save(v2)
    loaded = note_repo.get(fixed_id)
    assert loaded is not None
    assert loaded.title == "t2"
    assert loaded.content_md == "c2"


def test_regenerate_cards_append_not_overwrite(
    session: Session,
) -> None:
    """Saving new Cards for an existing Source preserves originals."""
    src_repo = SqlSourceRepository(session)
    card_repo = SqlCardRepository(session)

    src = Source(
        kind=SourceKind.TOPIC,
        user_prompt="p",
        display_name="d",
    )
    src_repo.save(src)

    first_batch = [
        Card(source_id=src.id, question=f"q{i}", answer=f"a{i}")
        for i in range(3)
    ]
    for c in first_batch:
        card_repo.save(c)

    second_batch = [
        Card(source_id=src.id, question=f"Q{i}", answer=f"A{i}")
        for i in range(3)
    ]
    for c in second_batch:
        card_repo.save(c)

    rows = (
        session.execute(
            select(CardRow).where(CardRow.source_id == str(src.id))
        )
        .scalars()
        .all()
    )
    assert len(rows) == 6

    # Original ids still resolve to the first-batch questions.
    for c in first_batch:
        loaded = card_repo.get(c.id)
        assert loaded is not None
        assert loaded.question == c.question
        assert loaded.answer == c.answer
