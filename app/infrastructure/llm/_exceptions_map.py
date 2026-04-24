# ABOUTME: Anthropic SDK exception → domain exception wrap helpers.
# ABOUTME: Context-overflow sniff + 429 / 400 payload extraction.
"""SDK → domain wrap helpers for AnthropicLLMProvider."""

from __future__ import annotations

import re
from typing import Any

import anthropic

from app.logging_config import get_logger

log = get_logger(__name__)

# Anthropic raises BadRequestError for both context-window overflow AND
# malformed tool-use schema. Sniff the message body for specific
# overflow markers; on match wrap as LLMContextTooLarge, else
# LLMRequestRejected (safe default — SC #4 must not retry 4xx).
#
# Markers are full phrases observed in Anthropic error messages as of
# anthropic SDK 0.97. Bare words like "context" or "payload" are
# deliberately excluded — they over-match unrelated 400s (e.g.
# "invalid payload structure" on a malformed tool schema).
CONTEXT_MARKERS: tuple[str, ...] = (
    "input is too long",
    "prompt is too long",
    "maximum context length",
    "exceeds the maximum context",
    "context_length_exceeded",
)

# Best-effort extractor for "N tokens ... M limit" patterns that
# sometimes appear in 400 bodies. Match failure -> payload fields stay
# None (we never raise on parse failure; the wrapping domain exception
# still carries the raw SDK message for diagnostics).
_CONTEXT_LEN_RE = re.compile(
    r"(\d[\d,]*)\s*tokens?.*?(?:maximum|limit|model)[^.]*?(\d[\d,]*)",
    re.IGNORECASE | re.DOTALL,
)


def is_context_overflow(err: anthropic.BadRequestError) -> bool:
    """Return True if the BadRequestError looks like context overflow.

    :param err: The SDK-raised BadRequestError to inspect.
    :returns: True when the error message contains any context-marker
        phrase from `CONTEXT_MARKERS`; False for non-overflow 400s.
    """
    msg = str(err).lower()
    return any(marker in msg for marker in CONTEXT_MARKERS)


def _extract_request_id(err: anthropic.APIError) -> str | None:
    """Pull the Anthropic request id for log correlation.

    Prefers the SDK's own `request_id` attribute (populated from the
    ``anthropic-request-id`` response header). Falls back to reading
    the header directly from the response when the attribute is
    absent (older SDK versions or mock-crafted errors).

    :param err: Any anthropic APIError subclass.
    :returns: The request id string, or None if neither source
        provides one.
    """
    rid = getattr(err, "request_id", None)
    if rid:
        return rid
    headers = getattr(getattr(err, "response", None), "headers", {}) or {}
    if hasattr(headers, "get"):
        return headers.get("anthropic-request-id")
    return None


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
            # RFC 7231 allows `retry-after` as an HTTP-date (e.g.
            # "Wed, 21 Oct 2026 07:28:00 GMT"). We do not parse that
            # form; log for visibility and fall through to tenacity's
            # exponential backoff instead.
            log.warning("llm.retry_after.unparsed", raw=raw)
            retry_after_ms = None
    return {
        "retry_after_ms": retry_after_ms,
        "request_id": _extract_request_id(err),
    }


def context_payload(err: anthropic.BadRequestError) -> dict[str, Any]:
    """Best-effort token-count extraction from a context-overflow 400.

    Anthropic sometimes surfaces "N tokens ... limit is M" phrasing in
    the error body; when that phrasing matches we fill `tokens` and
    `limit` on the domain exception. Match failure is not an error —
    the raw message still carries the details.

    :param err: SDK-raised BadRequestError already classified as
        context overflow by `is_context_overflow`.
    :returns: Kwargs dict suitable for `LLMContextTooLarge(**payload)`;
        fields default to `None` on match failure.
    """
    match = _CONTEXT_LEN_RE.search(str(err))
    if match is None:
        return {"tokens": None, "limit": None}
    try:
        tokens = int(match.group(1).replace(",", ""))
        limit = int(match.group(2).replace(",", ""))
    except (ValueError, IndexError):
        return {"tokens": None, "limit": None}
    return {"tokens": tokens, "limit": limit}
