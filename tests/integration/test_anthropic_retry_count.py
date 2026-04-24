# ABOUTME: SC #4 — respx proves tenacity attempts exact count.
# ABOUTME: Covers 429/500 retries, 401 whitelist skip, transport errors.
"""Anthropic retry-count integration tests (SC #4)."""

from __future__ import annotations

import anthropic
import httpx
import pytest
import respx
from tenacity import wait_fixed

from app.application.exceptions import LLMAuthFailed, LLMUnreachable
from app.infrastructure.llm.anthropic_provider import AnthropicLLMProvider

_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collapse tenacity wait to zero so retries add no wall-clock time.

    The `@retry` decorator captures the `wait_exponential(...)` result
    at class-definition time, so a module-attribute monkeypatch does
    NOT take effect on the already-decorated `_sdk_call`. Instead we
    reach through tenacity's `Retrying` instance (exposed as `.retry`
    on the decorated callable) and replace its `.wait` strategy — the
    same knob tenacity consults per attempt.
    """
    monkeypatch.setattr(
        AnthropicLLMProvider._sdk_call.retry, "wait", wait_fixed(0)
    )


def _valid_tool_use_body() -> dict:
    """Minimal valid messages.create response with a tool_use block."""
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-7",
        "stop_reason": "tool_use",
        "content": [
            {
                "type": "tool_use",
                "id": "tu_1",
                "name": "generate_note_and_cards",
                "input": {
                    "note": {"title": "t", "content_md": "c"},
                    "cards": [
                        {
                            "question": "q",
                            "answer": "a",
                            "tags": [],
                        }
                    ],
                },
            },
        ],
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def _fake_client() -> anthropic.Anthropic:
    """Muzzled client with a throwaway key; respx intercepts HTTP."""
    return anthropic.Anthropic(api_key="sk-ant-fake", max_retries=0)


@respx.mock
def test_429_then_200_exactly_two_calls() -> None:
    """SC #4: one 429 -> one 200 -> route.call_count == 2."""
    route = respx.post(_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(429, json={"error": {"type": "rate_limit_error"}}),
            httpx.Response(200, json=_valid_tool_use_body()),
        ]
    )
    provider = AnthropicLLMProvider(client=_fake_client())
    note, cards = provider.generate_note_and_cards(None, "alpha")
    assert route.call_count == 2
    assert note.title == "t"
    assert len(cards) == 1


@respx.mock
def test_401_no_retry_and_wraps_as_auth_failed() -> None:
    """SC #4 whitelist check: 401 -> 1 call, raises LLMAuthFailed."""
    route = respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            401,
            json={"error": {"type": "authentication_error"}},
        ),
    )
    provider = AnthropicLLMProvider(client=_fake_client())
    with pytest.raises(LLMAuthFailed):
        provider.generate_note_and_cards(None, "alpha")
    assert route.call_count == 1


@respx.mock
def test_500_then_500_then_200_exactly_three_calls() -> None:
    """SC #4: two 500s then a 200 -> route.call_count == 3."""
    route = respx.post(_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(500, json={"error": {"type": "api_error"}}),
            httpx.Response(500, json={"error": {"type": "api_error"}}),
            httpx.Response(200, json=_valid_tool_use_body()),
        ]
    )
    provider = AnthropicLLMProvider(client=_fake_client())
    note, cards = provider.generate_note_and_cards(None, "alpha")
    assert route.call_count == 3
    assert note.title == "t"
    assert len(cards) == 1


@respx.mock
def test_500_exhaustion_wraps_as_llm_unreachable() -> None:
    """SC #4: three 500s -> tenacity exhausts -> LLMUnreachable."""
    route = respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(500, json={"error": {"type": "api_error"}})
    )
    with pytest.raises(LLMUnreachable) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert route.call_count == 3
    assert isinstance(exc_info.value.__cause__, anthropic.InternalServerError)


@respx.mock
def test_connection_error_is_retried_and_wrapped() -> None:
    """APIConnectionError transients: 2 failures then success -> 3 calls."""
    route = respx.post(_MESSAGES_URL).mock(
        side_effect=[
            httpx.ConnectError("refused"),
            httpx.ConnectError("refused"),
            httpx.Response(200, json=_valid_tool_use_body()),
        ]
    )
    provider = AnthropicLLMProvider(client=_fake_client())
    note, _ = provider.generate_note_and_cards(None, "alpha")
    assert route.call_count == 3
    assert note.title == "t"


@respx.mock
def test_connection_exhaustion_wraps_as_llm_unreachable() -> None:
    """Three consecutive ConnectErrors -> LLMUnreachable."""
    route = respx.post(_MESSAGES_URL).mock(
        side_effect=httpx.ConnectError("refused")
    )
    with pytest.raises(LLMUnreachable) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert route.call_count == 3
    assert isinstance(exc_info.value.__cause__, anthropic.APIConnectionError)


@respx.mock
def test_timeout_error_is_retried_and_wrapped() -> None:
    """APITimeoutError is in the retry whitelist (D-03)."""
    route = respx.post(_MESSAGES_URL).mock(
        side_effect=[
            httpx.TimeoutException("slow"),
            httpx.Response(200, json=_valid_tool_use_body()),
        ]
    )
    provider = AnthropicLLMProvider(client=_fake_client())
    note, _ = provider.generate_note_and_cards(None, "alpha")
    assert route.call_count == 2
    assert note.title == "t"
