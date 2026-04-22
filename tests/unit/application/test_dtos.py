# ABOUTME: Pydantic DTO validation + frozen-dataclass tests.
# ABOUTME: Covers NoteDTO, CardDTO, GeneratedContent, Request/Response/Bundle.
"""Application DTO unit tests."""

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from app.application.dtos import (
    CardDTO,
    DraftBundle,
    GeneratedContent,
    GenerateRequest,
    GenerateResponse,
    NoteDTO,
)
from app.application.ports import DraftToken
from app.domain.value_objects import SourceKind


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


def test_generate_request_is_frozen() -> None:
    """GenerateRequest is a frozen stdlib dataclass."""
    req = GenerateRequest(
        kind=SourceKind.TOPIC, input=None, user_prompt="alpha"
    )
    with pytest.raises(FrozenInstanceError):
        req.user_prompt = "beta"  # type: ignore[misc]


def test_generate_request_allows_none_input_for_topic() -> None:
    """TOPIC kind constructs with input=None cleanly."""
    req = GenerateRequest(
        kind=SourceKind.TOPIC, input=None, user_prompt="alpha"
    )
    assert req.input is None
    assert req.kind is SourceKind.TOPIC


def test_generate_response_holds_token_and_bundle() -> None:
    """GenerateResponse exposes token and bundle attributes."""
    token = DraftToken(uuid.uuid4())
    bundle = DraftBundle(
        note=NoteDTO(title="t", content_md="c"),
        cards=[CardDTO(question="q?", answer="a.")],
    )
    response = GenerateResponse(token=token, bundle=bundle)
    assert response.token is token
    assert response.bundle is bundle


def test_draft_bundle_is_frozen() -> None:
    """DraftBundle is a frozen stdlib dataclass."""
    bundle = DraftBundle(
        note=NoteDTO(title="t", content_md="c"),
        cards=[CardDTO(question="q?", answer="a.")],
    )
    with pytest.raises(FrozenInstanceError):
        bundle.note = NoteDTO(title="x", content_md="y")  # type: ignore[misc]
