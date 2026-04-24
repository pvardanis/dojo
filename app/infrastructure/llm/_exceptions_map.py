# ABOUTME: Anthropic SDK exception → domain exception wrap helpers.
# ABOUTME: Dispatch table + sniff + 429/400 payload extraction.
"""SDK → domain wrap helpers for AnthropicLLMProvider."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import anthropic

# These four SDK error classes live in `anthropic._exceptions` and
# aren't re-exported from the top-level `anthropic` module in SDK
# 0.97. Import them directly so `ty` resolves the symbols. If a
# future SDK version promotes them to the public namespace, this
# block can be swapped for `anthropic.ServiceUnavailableError` etc.
from anthropic._exceptions import (  # type: ignore[import-not-found]
    DeadlineExceededError,
    OverloadedError,
    RequestTooLargeError,
    ServiceUnavailableError,
)

from app.application.exceptions import (
    DojoError,
    LLMAuthFailed,
    LLMContextTooLarge,
    LLMRateLimited,
    LLMRequestRejected,
    LLMUnreachable,
)
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


# --- SDK → domain dispatch --------------------------------------------
#
# Individual wrapper helpers — each is declared with its narrow SDK
# type so the payload extractors typecheck, but the dispatch table
# stores them as `Callable[[Any], DojoError]` because the runtime
# pairing is guaranteed by `isinstance(err, sdk_cls)` in
# `wrap_sdk_error`.


def _wrap_rate_limit(err: anthropic.RateLimitError) -> DojoError:
    """Wrap RateLimitError with retry-after + request-id payload."""
    return LLMRateLimited(str(err), **rate_limit_payload(err))


def _wrap_auth_failed(err: anthropic.APIError) -> DojoError:
    """Wrap 401 / 403 errors as LLMAuthFailed (no retry)."""
    return LLMAuthFailed(str(err))


def _wrap_unreachable(err: anthropic.APIError) -> DojoError:
    """Wrap connection, timeout, and 5xx errors as LLMUnreachable."""
    return LLMUnreachable(str(err))


def _wrap_bad_request(err: anthropic.BadRequestError) -> DojoError:
    """Split 400s into LLMContextTooLarge vs LLMRequestRejected.

    Uses `is_context_overflow` + `context_payload` to distinguish
    a real context-window overflow (retryable by shrinking input)
    from any other permanent 4xx (malformed tool schema, etc.).
    """
    if is_context_overflow(err):
        return LLMContextTooLarge(str(err), **context_payload(err))
    return LLMRequestRejected(str(err))


def _wrap_rejected(err: anthropic.APIError) -> DojoError:
    """Wrap other permanent 4xx errors as LLMRequestRejected."""
    return LLMRequestRejected(str(err))


# Specificity order: subclasses before superclasses.
# `isinstance(err, sdk_cls)` picks the first match. Adding a new
# mapping = append one row here (plus a `_wrap_*` helper if the
# existing ones don't fit) — `wrap_sdk_error` itself doesn't change.
_SDK_DISPATCH: tuple[
    tuple[type[anthropic.APIError], Callable[[Any], DojoError]], ...
] = (
    (anthropic.RateLimitError, _wrap_rate_limit),
    (anthropic.AuthenticationError, _wrap_auth_failed),
    (anthropic.PermissionDeniedError, _wrap_auth_failed),
    (anthropic.APITimeoutError, _wrap_unreachable),
    (anthropic.APIConnectionError, _wrap_unreachable),
    (anthropic.InternalServerError, _wrap_unreachable),
    (ServiceUnavailableError, _wrap_unreachable),
    (OverloadedError, _wrap_unreachable),
    (DeadlineExceededError, _wrap_unreachable),
    (anthropic.BadRequestError, _wrap_bad_request),
    (anthropic.ConflictError, _wrap_rejected),
    (anthropic.NotFoundError, _wrap_rejected),
    (RequestTooLargeError, _wrap_rejected),
    (anthropic.UnprocessableEntityError, _wrap_rejected),
    (anthropic.APIResponseValidationError, _wrap_rejected),
)


def mapped_sdk_types() -> set[type[anthropic.APIError]]:
    """Return the SDK error classes currently covered by the dispatch.

    Exposed so the tripwire test can assert every concrete SDK
    subclass either appears here or is handled via a superclass
    entry in ``_SDK_DISPATCH``.

    :returns: Set of SDK error classes with explicit dispatch rows.
    """
    return {cls for cls, _ in _SDK_DISPATCH}


def wrap_sdk_error(err: anthropic.APIError) -> DojoError:
    """Translate any SDK error to its domain counterpart.

    Walks ``_SDK_DISPATCH`` and returns the first wrapper whose class
    filter matches. A subclass that falls through every explicit row
    ends up at the ``LLMRequestRejected`` default — a permanent 4xx
    equivalent that does NOT retry, so an unknown SDK error becomes
    a user-visible permanent error rather than a raw SDK leak past
    the domain boundary.

    :param err: SDK-raised exception to translate.
    :returns: A ``DojoError`` subclass; callers chain it with
        ``raise wrap_sdk_error(err) from err``.
    """
    for sdk_cls, wrapper in _SDK_DISPATCH:
        if isinstance(err, sdk_cls):
            return wrapper(err)
    return LLMRequestRejected(str(err))
