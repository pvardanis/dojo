# ABOUTME: Stdlib frozen-dataclass tests for internal use-case DTOs.
# ABOUTME: Covers GenerateRequest, GenerateResponse, DraftBundle.
"""Use-case DTO unit tests (stdlib frozen dataclasses)."""

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError

import pytest

from app.application.dtos import (
    CardDTO,
    DraftBundle,
    GenerateRequest,
    GenerateResponse,
    NoteDTO,
)
from app.application.ports import DraftToken
from app.domain.value_objects import SourceKind


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
