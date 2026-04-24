# ABOUTME: SC #2 — forced 3rd-save failure triggers 3-row rollback.
# ABOUTME: Pattern Phase 4's SaveDraft will reuse verbatim.
"""Atomic persistence — SC #2 (Source + Note + Cards rollback)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities import Card, Note, Source
from app.domain.value_objects import CardId, SourceKind
from app.infrastructure.db.models import CardRow, NoteRow, SourceRow
from app.infrastructure.repositories.sql_card_repository import (
    SqlCardRepository,
)
from app.infrastructure.repositories.sql_note_repository import (
    SqlNoteRepository,
)
from app.infrastructure.repositories.sql_source_repository import (
    SqlSourceRepository,
)


def test_third_save_failure_rolls_back_all_three(
    session: Session,
) -> None:
    """SC #2: forced card-save fail → Source + Note + Card absent.

    Wraps the three saves in `session.begin_nested()` (a SAVEPOINT
    under the conftest fixture's outer transaction) so that raising
    from `card_repo.save(card_b)` rolls back the SAVEPOINT cleanly
    without terminating the outer fixture transaction. This is the
    same rollback-on-exception semantic Phase 4's
    `with session.begin():` will use; SQLAlchemy treats nested and
    outer transaction contexts symmetrically for this behaviour.
    """
    src_repo = SqlSourceRepository(session)
    note_repo = SqlNoteRepository(session)
    card_repo = SqlCardRepository(session)

    src = Source(
        kind=SourceKind.TOPIC,
        user_prompt="p",
        display_name="d",
    )
    note = Note(source_id=src.id, title="t", content_md="c")
    duplicate_id = CardId(uuid.uuid4())
    card_a = Card(
        source_id=src.id,
        question="q",
        answer="a",
        id=duplicate_id,
    )
    card_b = Card(
        source_id=src.id,
        question="q2",
        answer="a2",
        id=duplicate_id,  # PK collision → IntegrityError at flush
    )

    with pytest.raises(IntegrityError), session.begin_nested():
        src_repo.save(src)
        note_repo.save(note)
        card_repo.save(card_a)
        card_repo.save(card_b)

    # After the nested SAVEPOINT rolls back, none of the three rows
    # are observable through the still-live outer transaction.
    assert session.get(SourceRow, str(src.id)) is None
    assert session.get(NoteRow, str(note.id)) is None
    assert session.get(CardRow, str(duplicate_id)) is None
