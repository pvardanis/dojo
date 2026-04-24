# ABOUTME: SC #3 — Pydantic DTO validation + semantic retry + wrap.
# ABOUTME: respx stubs drive malformed -> retry -> raise sequences.
"""Anthropic provider integration tests (SC #3)."""

from __future__ import annotations

import json
from typing import Any

import anthropic
import httpx
import pytest
import respx
from tenacity import wait_fixed

from app.application.dtos import CardDTO, NoteDTO
from app.application.exceptions import (
    LLMAuthFailed,
    LLMContextTooLarge,
    LLMOutputMalformed,
    LLMRateLimited,
    LLMRequestRejected,
)
from app.infrastructure.llm.anthropic_provider import AnthropicLLMProvider
from app.settings import get_settings

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
    """SC #4: 3x 429 -> tenacity exhausts -> LLMRateLimited (w/ __cause__)."""
    route = respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            429, json={"error": {"type": "rate_limit_error"}}
        )
    )
    with pytest.raises(LLMRateLimited) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert route.call_count == 3
    # __cause__ chain must survive tenacity + outer wrap so the
    # underlying SDK exception stays visible in tracebacks.
    assert isinstance(exc_info.value.__cause__, anthropic.RateLimitError)


@respx.mock
def test_rate_limit_populates_structured_payload() -> None:
    """LLMRateLimited carries retry_after_ms + request_id from headers."""
    respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            429,
            json={"error": {"type": "rate_limit_error"}},
            headers={
                "retry-after": "12",
                "anthropic-request-id": "req_abc",
            },
        )
    )
    with pytest.raises(LLMRateLimited) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    exc = exc_info.value
    assert exc.retry_after_ms == 12000
    assert exc.request_id == "req_abc"


@respx.mock
def test_bad_request_context_overflow_wraps_as_context_too_large() -> None:
    """Context-overflow 400 wraps as LLMContextTooLarge + tokens/limit."""
    respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "type": "invalid_request_error",
                    "message": (
                        "Input is too long: 210,000 tokens, but the "
                        "model has a maximum context length of 200,000."
                    ),
                }
            },
        )
    )
    with pytest.raises(LLMContextTooLarge) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    exc = exc_info.value
    assert exc.tokens == 210000
    assert exc.limit == 200000
    assert isinstance(exc.__cause__, anthropic.BadRequestError)


@respx.mock
def test_bad_request_non_overflow_wraps_as_request_rejected() -> None:
    """Non-overflow 400 wraps as LLMRequestRejected, NOT LLMContextTooLarge.

    Guards the sniff markers: a generic 400 whose message happens to
    mention words like "context" in prose must route to the safe
    default (no retry, no context-shrink logic upstream).
    """
    respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "type": "invalid_request_error",
                    "message": "tool schema invalid: property 'cards' missing",
                }
            },
        )
    )
    with pytest.raises(LLMRequestRejected) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert isinstance(exc_info.value.__cause__, anthropic.BadRequestError)


@respx.mock
def test_403_wraps_as_auth_failed() -> None:
    """PermissionDeniedError (403) -> LLMAuthFailed (no retry)."""
    route = respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            403, json={"error": {"type": "permission_error"}}
        )
    )
    with pytest.raises(LLMAuthFailed) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert route.call_count == 1
    assert isinstance(
        exc_info.value.__cause__, anthropic.PermissionDeniedError
    )


@respx.mock
def test_404_wraps_as_request_rejected() -> None:
    """NotFoundError (404) -> LLMRequestRejected (no retry)."""
    route = respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            404, json={"error": {"type": "not_found_error"}}
        )
    )
    with pytest.raises(LLMRequestRejected) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert route.call_count == 1
    assert isinstance(exc_info.value.__cause__, anthropic.NotFoundError)


@respx.mock
def test_422_wraps_as_request_rejected() -> None:
    """UnprocessableEntityError (422) -> LLMRequestRejected (no retry)."""
    route = respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            422, json={"error": {"type": "invalid_request_error"}}
        )
    )
    with pytest.raises(LLMRequestRejected) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert route.call_count == 1
    assert isinstance(
        exc_info.value.__cause__, anthropic.UnprocessableEntityError
    )


@respx.mock
def test_auth_failed_preserves_cause_chain() -> None:
    """AuthenticationError (401) -> LLMAuthFailed has SDK __cause__."""
    respx.post(_MESSAGES_URL).mock(
        return_value=httpx.Response(
            401, json={"error": {"type": "authentication_error"}}
        )
    )
    with pytest.raises(LLMAuthFailed) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    assert isinstance(exc_info.value.__cause__, anthropic.AuthenticationError)


@respx.mock
def test_malformed_then_malformed_cause_chain() -> None:
    """Double malformed -> LLMOutputMalformed with pydantic VE as cause."""
    respx.post(_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(200, json=_tool_use_body([])),
            httpx.Response(200, json=_tool_use_body([])),
        ]
    )
    with pytest.raises(LLMOutputMalformed) as exc_info:
        AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
            None, "alpha"
        )
    # pydantic.ValidationError inherits from ValueError; we only assert
    # the cause is a ValidationError so a future pydantic bump of the
    # base class hierarchy doesn't break the test.
    assert exc_info.value.__cause__ is not None
    assert type(exc_info.value.__cause__).__name__ == "ValidationError"


@respx.mock
def test_semantic_retry_sends_stricter_system_prompt() -> None:
    """The second call's `system` field carries the stricter addendum.

    Without this assertion, the stricter prompt could be silently
    dropped during a refactor and SC #3's retry quality degrades.
    """
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
    AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
        None, "alpha"
    )
    assert route.call_count == 2
    first_body = json.loads(route.calls[0].request.content)
    second_body = json.loads(route.calls[1].request.content)
    assert "MUST contain at least one card" not in first_body["system"]
    assert "MUST contain at least one card" in second_body["system"]


@respx.mock
def test_semantic_retry_emits_warning_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured warning fires on semantic retry with validation_error.

    Patches the module-level structlog logger's `warning` method
    directly. `caplog` only captures stdlib records and
    `structlog.testing.capture_logs` mutates global processors in a
    way that can leak into subsequent tests, so we use a local
    monkeypatch that reverts automatically at teardown.
    """
    from app.infrastructure.llm import anthropic_provider as provider_module

    calls: list[dict[str, Any]] = []

    def _record(event: str, **kwargs: Any) -> None:
        """Capture `log.warning(event, **kwargs)` calls for assertion."""
        calls.append({"event": event, **kwargs})

    monkeypatch.setattr(provider_module.log, "warning", _record)

    respx.post(_MESSAGES_URL).mock(
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
    AnthropicLLMProvider(client=_fake_client()).generate_note_and_cards(
        None, "alpha"
    )
    assert len(calls) == 1
    call = calls[0]
    assert call["event"] == "llm.malformed.retrying_stricter"
    # validation_error carries the pydantic reason for diagnostics.
    assert "validation_error" in call
    assert "cards" in call["validation_error"]


@respx.mock
def test_multiple_tool_blocks_picks_first() -> None:
    """Multiple tool_use blocks in response -> parser uses the first one.

    Pins the current "first-wins" behavior so a refactor can't silently
    switch to "last-wins" or "merge" without updating this test.
    """
    body: dict[str, Any] = {
        "id": "msg",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-7",
        "stop_reason": "tool_use",
        "content": [
            {
                "type": "tool_use",
                "id": "tu_first",
                "name": "generate_note_and_cards",
                "input": {
                    "note": {"title": "FIRST", "content_md": "c1"},
                    "cards": [{"question": "q1", "answer": "a1", "tags": []}],
                },
            },
            {
                "type": "tool_use",
                "id": "tu_second",
                "name": "generate_note_and_cards",
                "input": {
                    "note": {"title": "SECOND", "content_md": "c2"},
                    "cards": [{"question": "q2", "answer": "a2", "tags": []}],
                },
            },
        ],
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }
    respx.post(_MESSAGES_URL).mock(return_value=httpx.Response(200, json=body))
    note, cards = AnthropicLLMProvider(
        client=_fake_client()
    ).generate_note_and_cards(None, "alpha")
    assert note.title == "FIRST"
    assert cards[0].question == "q1"


def test_default_client_uses_max_retries_zero_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production path sets max_retries=0 + timeout (PITFALL C7).

    The integration tests inject a pre-built `_fake_client()` so they
    never exercise the default-client branch. Without this unit test,
    a future refactor that drops `max_retries=0` would silently stack
    the SDK's retry loop on top of tenacity and 3x the SC #4 counts —
    and nothing would fail.
    """
    captured: dict[str, Any] = {}

    class _RecordingAnthropic:
        """Minimal stand-in for anthropic.Anthropic that captures kwargs."""

        def __init__(self, **kwargs: Any) -> None:
            """Record the constructor kwargs for later assertion."""
            captured.update(kwargs)

    monkeypatch.setattr(
        "app.infrastructure.llm.anthropic_provider.anthropic.Anthropic",
        _RecordingAnthropic,
    )
    get_settings.cache_clear()
    AnthropicLLMProvider()
    assert captured["max_retries"] == 0
    assert captured["timeout"] == 30.0
    # Don't hardcode the key — CI sets ANTHROPIC_API_KEY=ci-placeholder
    # while local dev falls back to "dev-placeholder". Pull the same
    # settings the production code uses so this passes everywhere.
    expected_key = get_settings().anthropic_api_key.get_secret_value()
    assert captured["api_key"] == expected_key
