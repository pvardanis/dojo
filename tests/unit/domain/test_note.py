# ABOUTME: Unit tests for Note entity — title + content_md invariants.
# ABOUTME: Exercises __post_init__ ValueError and frozen-dataclass semantics.
"""Unit tests for Note entity."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime

import pytest

from app.domain.entities import Note
from app.domain.value_objects import SourceId


def _make_source_id() -> SourceId:
    """Mint a fresh SourceId for tests that need a parent reference."""
    return SourceId(uuid.uuid4())


def test_note_constructs_with_title_and_content_md() -> None:
    """Note builds with title + content_md + source_id."""
    n = Note(
        source_id=_make_source_id(),
        title="k8s intro",
        content_md="# k8s\n\nbasics",
    )
    assert n.title == "k8s intro"
    assert n.content_md == "# k8s\n\nbasics"


def test_note_rejects_empty_title() -> None:
    """Note construction raises ValueError on whitespace-only title."""
    with pytest.raises(ValueError, match="title"):
        Note(
            source_id=_make_source_id(),
            title="   ",
            content_md="content",
        )


def test_note_rejects_empty_content_md() -> None:
    """Note construction raises ValueError on empty content_md."""
    with pytest.raises(ValueError, match="content_md"):
        Note(
            source_id=_make_source_id(),
            title="t",
            content_md="",
        )


def test_note_carries_source_id_association() -> None:
    """Note stores the SourceId it was constructed with."""
    sid = _make_source_id()
    n = Note(source_id=sid, title="t", content_md="c")
    assert n.source_id is sid


def test_note_id_is_unique() -> None:
    """Two Notes constructed back-to-back have distinct ids."""
    a = Note(source_id=_make_source_id(), title="t", content_md="c")
    b = Note(source_id=_make_source_id(), title="t", content_md="c")
    assert a.id != b.id
    assert isinstance(a.id, uuid.UUID)


def test_note_is_frozen() -> None:
    """Frozen dataclass: direct attribute assignment raises."""
    n = Note(source_id=_make_source_id(), title="t", content_md="c")
    with pytest.raises(dataclasses.FrozenInstanceError):
        n.title = "changed"  # type: ignore[misc]


def test_note_equality_and_hash() -> None:
    """Two freshly-constructed Notes are NOT equal (distinct ids); hashable."""
    sid = _make_source_id()
    a = Note(source_id=sid, title="t", content_md="c")
    b = Note(source_id=sid, title="t", content_md="c")
    assert a != b
    assert a == a
    assert {a, a} == {a}


def test_note_rejects_naive_generated_at() -> None:
    """Note construction with a naive datetime raises ValueError."""
    with pytest.raises(
        ValueError, match="generated_at must be timezone-aware"
    ):
        Note(
            source_id=_make_source_id(),
            title="t",
            content_md="c",
            generated_at=datetime(2026, 4, 22, 9, 0, 0),
        )
