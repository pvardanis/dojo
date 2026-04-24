# ABOUTME: SC #3 — Pydantic DTO validation + semantic retry + wrap.
# ABOUTME: respx stubs drive malformed -> retry -> raise sequences.
"""Anthropic provider integration tests (SC #3)."""

from __future__ import annotations

import anthropic
import httpx
import pytest
import respx
from tenacity import wait_fixed

from app.application.dtos import CardDTO, NoteDTO
from app.application.exceptions import LLMOutputMalformed, LLMRateLimited
from app.infrastructure.llm.anthropic_provider import AnthropicLLMProvider

_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collapse tenacity wait to zero on the decorated _sdk_call.

    See `test_anthropic_retry_count._fast_retries` for the rationale
    behind patching `.retry.wait` (not the module-level symbol).
    """
    monkeypatch.setattr(
        AnthropicLLMProvider._sdk_call.retry, "wait", wait_fixed(0)
    )


def _tool_use_body(cards: list[dict]) -> dict:
    """Build a response body with a parameterised cards list."""
    return {
        "id": "msg",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-7",
        "stop_reason": "tool_use",
        "content": [
            {
                "type": "tool_use",
                "id": "tu",
                "name": "generate_note_and_cards",
                "input": {
                    "note": {"title": "t", "content_md": "c"},
                    "cards": cards,
                },
            }
        ],
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def _fake_client() -> anthropic.Anthropic:
    """Muzzled client with a throwaway key; respx intercepts HTTP."""
    return anthropic.Anthropic(api_key="sk-ant-fake", max_retries=0)


@respx.mock
def test_valid_response_returns_note_and_cards() -> None:
    """Happy path: valid tool_use -> (NoteDTO, [CardDTO])."""
    respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json=_tool_use_body(
                [{"question": "q", "answer": "a", "tags": []}]
            ),
        )
    )
    note, cards = AnthropicLLMProvider(
        client=_fake_client()
    ).generate_note_and_cards(None, "alpha")
    assert isinstance(note, NoteDTO)
    assert len(cards) == 1
    assert isinstance(cards[0], CardDTO)


@respx.mock
def test_empty_cards_then_valid_triggers_semantic_retry() -> None:
    """SC #3: empty cards -> pydantic.ValidationError -> one retry."""
    route = respx.post(_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(200, json=_tool_use_body([])),
            httpx.Response(
                200,
                json=_tool_use_body(
                    [{"question": "q", "answer": "a", "tags": []}]
                ),
            ),
        ]
    )
    note, cards = AnthropicLLMProvider(
        client=_fake_client()
    ).generate_note_and_cards(None, "alpha")
    assert route.call_count == 2
    assert len(cards) == 1
    assert note.title == "t"


@respx.mock
def test_both_empty_cards_raises_malformed_after_retry() -> None:
    """SC #3: empty cards twice -> LLMOutputMalformed after one retry."""
    route = respx.post(_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(200, json=_tool_use_body([])),
            httpx.Response(200, json=_tool_use_body([])),
        ]
    )
    with pytest.raises(LLMOutputMalformed):
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert route.call_count == 2


@respx.mock
def test_response_without_tool_use_block_raises_malformed() -> None:
    """SC #3: no tool_use block -> LLMOutputMalformed immediately."""
    respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "m",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-4-7",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "hello"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )
    )
    with pytest.raises(LLMOutputMalformed, match="no tool_use"):
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )


@respx.mock
def test_rate_limit_exhaustion_wraps_as_llm_rate_limited() -> None:
    """SC #4: 3x 429 -> tenacity exhausts -> LLMRateLimited."""
    route = respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            429, json={"error": {"type": "rate_limit_error"}}
        )
    )
    with pytest.raises(LLMRateLimited):
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert route.call_count == 3
