# ABOUTME: Pydantic DTO validation tests — LLM I/O trust-boundary shape.
# ABOUTME: Covers NoteDTO, CardDTO, GeneratedContent (extra=ignore + min).
"""Pydantic DTO unit tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.application.dtos import CardDTO, GeneratedContent, NoteDTO


def test_card_dto_rejects_empty_question() -> None:
    """CardDTO raises ValidationError when question is empty."""
    with pytest.raises(ValidationError):
        CardDTO(question="", answer="a.")


def test_card_dto_rejects_empty_answer() -> None:
    """CardDTO raises ValidationError when answer is empty."""
    with pytest.raises(ValidationError):
        CardDTO(question="q?", answer="")


def test_card_dto_default_tags_is_empty_tuple() -> None:
    """CardDTO.tags defaults to ()."""
    card = CardDTO(question="q?", answer="a.")
    assert card.tags == ()


def test_card_dto_ignores_extra_fields() -> None:
    """CardDTO with extra='ignore' silently drops unknown keys."""
    card = CardDTO(question="q?", answer="a.", bogus="x")
    assert not hasattr(card, "bogus")


def test_note_dto_rejects_empty_title() -> None:
    """NoteDTO raises ValidationError when title is empty."""
    with pytest.raises(ValidationError):
        NoteDTO(title="", content_md="body")


def test_note_dto_rejects_empty_content() -> None:
    """NoteDTO raises ValidationError when content_md is empty."""
    with pytest.raises(ValidationError):
        NoteDTO(title="t", content_md="")


def test_note_dto_ignores_extra_fields() -> None:
    """NoteDTO with extra='ignore' silently drops unknown keys."""
    note = NoteDTO(title="t", content_md="c", bogus="x")
    assert not hasattr(note, "bogus")


def test_generated_content_requires_at_least_one_card() -> None:
    """GeneratedContent rejects an empty cards list (PITFALL M6)."""
    with pytest.raises(ValidationError):
        GeneratedContent(
            note=NoteDTO(title="t", content_md="c"),
            cards=[],
        )


def test_generated_content_accepts_single_card() -> None:
    """GeneratedContent accepts a non-empty cards list."""
    content = GeneratedContent(
        note=NoteDTO(title="t", content_md="c"),
        cards=[CardDTO(question="q?", answer="a.")],
    )
    assert len(content.cards) == 1
