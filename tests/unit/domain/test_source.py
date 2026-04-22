# ABOUTME: Unit tests for Source entity (kind/identifier coherence).
# ABOUTME: Exercises __post_init__ ValueError paths and frozen semantics.
"""Unit tests for Source entity."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime

import pytest

from app.domain.entities import Source
from app.domain.value_objects import SourceKind


def test_topic_source_constructs_with_prompt_and_display_name() -> None:
    """TOPIC source needs only user_prompt + display_name."""
    s = Source(
        kind=SourceKind.TOPIC,
        user_prompt="intro to k8s",
        display_name="k8s basics",
    )
    assert s.kind is SourceKind.TOPIC
    assert s.identifier is None
    assert s.source_text is None


def test_file_source_carries_identifier_and_source_text() -> None:
    """FILE source carries both identifier and source_text."""
    s = Source(
        kind=SourceKind.FILE,
        user_prompt="summarise",
        display_name="k8s patterns wiki",
        identifier="/path/to/file.md",
        source_text="# k8s patterns\n\ncontent here",
    )
    assert s.identifier == "/path/to/file.md"
    assert s.source_text == "# k8s patterns\n\ncontent here"


def test_url_source_carries_identifier_and_source_text() -> None:
    """URL source carries both identifier and source_text."""
    s = Source(
        kind=SourceKind.URL,
        user_prompt="summarise",
        display_name="trafilatura article",
        identifier="https://example.com/article",
        source_text="extracted article body",
    )
    assert s.identifier == "https://example.com/article"


def test_source_rejects_empty_user_prompt() -> None:
    """Source construction raises ValueError on whitespace-only user_prompt."""
    with pytest.raises(ValueError, match="user_prompt"):
        Source(
            kind=SourceKind.TOPIC,
            user_prompt="   ",
            display_name="x",
        )


def test_source_rejects_empty_display_name() -> None:
    """Source construction raises ValueError on empty display_name."""
    with pytest.raises(ValueError, match="display_name"):
        Source(
            kind=SourceKind.TOPIC,
            user_prompt="x",
            display_name="",
        )


def test_topic_rejects_identifier() -> None:
    """TOPIC source with a non-None identifier is illegal."""
    with pytest.raises(
        ValueError, match="TOPIC source must not carry identifier"
    ):
        Source(
            kind=SourceKind.TOPIC,
            user_prompt="x",
            display_name="t",
            identifier="/tmp/file.md",
        )


def test_topic_rejects_source_text() -> None:
    """TOPIC source with a non-None source_text is illegal."""
    with pytest.raises(
        ValueError, match="TOPIC source must not carry source_text"
    ):
        Source(
            kind=SourceKind.TOPIC,
            user_prompt="x",
            display_name="t",
            source_text="leaked content",
        )


def test_file_rejects_missing_identifier() -> None:
    """FILE source without identifier raises."""
    with pytest.raises(
        ValueError, match="file source requires non-empty identifier"
    ):
        Source(
            kind=SourceKind.FILE,
            user_prompt="x",
            display_name="t",
            source_text="content",
        )


def test_url_rejects_missing_source_text() -> None:
    """URL source without source_text raises."""
    with pytest.raises(
        ValueError, match="url source requires non-empty source_text"
    ):
        Source(
            kind=SourceKind.URL,
            user_prompt="x",
            display_name="t",
            identifier="https://example.com",
        )


def test_source_id_is_unique_per_instance() -> None:
    """Two Sources constructed back-to-back have distinct ids."""
    a = Source(kind=SourceKind.TOPIC, user_prompt="x", display_name="t")
    b = Source(kind=SourceKind.TOPIC, user_prompt="x", display_name="t")
    assert a.id != b.id
    assert isinstance(a.id, uuid.UUID)


def test_source_is_frozen() -> None:
    """Frozen dataclass: direct attribute assignment raises."""
    s = Source(kind=SourceKind.TOPIC, user_prompt="x", display_name="t")
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.user_prompt = "changed"  # type: ignore[misc]


def test_source_rejects_naive_created_at() -> None:
    """Source construction with a naive datetime raises ValueError."""
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        Source(
            kind=SourceKind.TOPIC,
            user_prompt="x",
            display_name="t",
            created_at=datetime(2026, 4, 22, 9, 0, 0),
        )
