# ABOUTME: Unit tests for Source entity — structural + frozen semantics.
# ABOUTME: Validation lives at boundary layers; domain is pure data.
"""Unit tests for Source entity."""

from __future__ import annotations

import dataclasses
import uuid

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
