# ABOUTME: Unit tests for Note entity — structural + frozen semantics.
# ABOUTME: Validation lives at boundary layers; domain is pure data.
"""Unit tests for Note entity."""

from __future__ import annotations

import dataclasses
import uuid

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
