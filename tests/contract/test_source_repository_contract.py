# ABOUTME: TEST-03 contract harness — asserts SourceRepository shape.
# ABOUTME: Fake leg always runs; sql leg uses the session fixture.
"""SourceRepository contract tests — fake + sql impls."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.domain.entities import Source
from app.domain.value_objects import SourceId, SourceKind
from tests.fakes import FakeSourceRepository


@pytest.fixture(params=["fake", "sql"])
def source_repository(
    request: pytest.FixtureRequest,
    session: Session,
) -> Iterator:
    """Yield a fake or real SourceRepository."""
    if request.param == "fake":
        yield FakeSourceRepository()
        return
    from app.infrastructure.repositories.sql_source_repository import (
        SqlSourceRepository,
    )

    yield SqlSourceRepository(session)


def test_save_then_get_roundtrips(source_repository) -> None:
    """Saved Source is retrievable by id with every field preserved."""
    src = Source(
        kind=SourceKind.TOPIC,
        user_prompt="x",
        display_name="y",
    )
    source_repository.save(src)
    loaded = source_repository.get(src.id)
    assert loaded is not None
    assert loaded.id == src.id
    assert loaded.user_prompt == "x"
    assert loaded.display_name == "y"
    assert loaded.kind is SourceKind.TOPIC


def test_get_unknown_returns_none(source_repository) -> None:
    """Unknown id returns None, not a raise."""
    loaded = source_repository.get(SourceId(uuid.uuid4()))
    assert loaded is None
