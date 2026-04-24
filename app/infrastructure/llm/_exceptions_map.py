# ABOUTME: Anthropic SDK exception → domain exception wrap helpers.
# ABOUTME: Context-overflow sniff markers + 429 payload extraction.
"""SDK → domain wrap helpers for AnthropicLLMProvider."""

from __future__ import annotations

from typing import Any

import anthropic

# Anthropic raises BadRequestError for both context-window overflow AND
# malformed tool-use schema. Sniff the message body for context
# markers; on match wrap as LLMContextTooLarge, else LLMRequestRejected.
# Heuristic — expand the list if real traffic surfaces a variant
# string.
CONTEXT_MARKERS: tuple[str, ...] = (
    "maximum context length",
    "context_length_exceeded",
    "prompt is too long",
    "context window",
    "payload",
    "context",
)


def is_context_overflow(err: anthropic.BadRequestError) -> bool:
    """Return True if the BadRequestError looks like context overflow.

    :param err: The SDK-raised BadRequestError to inspect.
    :returns: True when the error message contains any context-marker
        substring; False for non-context 400s.
    """
    msg = str(err).lower()
    return any(marker in msg for marker in CONTEXT_MARKERS)


def rate_limit_payload(err: anthropic.RateLimitError) -> dict[str, Any]:
    """Extract retry-after (ms) and request-id from a 429 response.

    :param err: The SDK-raised RateLimitError carrying the HTTP
        response (may lack headers on some test stubs).
    :returns: Kwargs dict suitable for `LLMRateLimited(**payload)`;
        missing fields are set to `None`.
    """
    headers = getattr(getattr(err, "response", None), "headers", {}) or {}
    retry_after_ms: int | None = None
    raw = headers.get("retry-after") if hasattr(headers, "get") else None
    if raw is not None:
        try:
            retry_after_ms = int(float(raw) * 1000)
        except (TypeError, ValueError):
            retry_after_ms = None
    request_id = headers.get("request-id") if hasattr(headers, "get") else None
    return {"retry_after_ms": retry_after_ms, "request_id": request_id}
