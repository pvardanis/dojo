# ABOUTME: Application-layer exception hierarchy.
# ABOUTME: Every class inherits from app.domain.exceptions.DojoError.
"""Application-layer exceptions."""

from __future__ import annotations

from app.domain.exceptions import DojoError


class UnsupportedSourceKind(DojoError):
    """Raised when a source kind is not yet supported by the use case."""


class ExtractorNotApplicable(DojoError):
    """Raised when a SourceKind categorically has no extractor.

    Distinct from `UnsupportedSourceKind`: this signals a category
    mismatch (e.g. TOPIC, whose source text is `None` by design and
    must bypass the registry), not a "not wired up yet" state.
    """


class DraftExpired(DojoError):
    """Raised when a draft token has expired or was already popped."""


class LLMOutputMalformed(DojoError):
    """Raised when the LLM's structured output fails DTO validation."""


class LLMRateLimited(DojoError):
    """Raised after all tenacity retries exhaust on a 429 response."""


class LLMAuthFailed(DojoError):
    """Raised when the provider rejects credentials (401 or 403)."""


class LLMUnreachable(DojoError):
    """Raised on transport failure after tenacity retries."""


class LLMContextTooLarge(DojoError):
    """Raised when the payload exceeds the model's context window."""


class LLMInvalidRequest(DojoError):
    """Raised on permanent 4xx (non-auth, non-context-size)."""


class SourceNotFound(DojoError):
    """Raised when a FILE path does not exist."""


class SourceUnreadable(DojoError):
    """Raised when a FILE path cannot be read as UTF-8 text."""


class SourceFetchFailed(DojoError):
    """Raised on URL fetch failure (non-2xx, timeout, transport)."""


class SourceNotArticle(DojoError):
    """Raised when extraction yields no usable article text."""
