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


class LLMError(DojoError):
    """Base class for LLM-provider failures.

    Adapters tenacity-retry against this base for transient failures,
    and route handlers catch it to render a single generic error
    partial. Specific subclasses preserve the failure-mode distinction
    for callers that need to route differently (e.g. auth failures
    must not retry; rate-limit failures report a suggested backoff).
    """


class LLMOutputMalformed(LLMError):
    """Raised when the LLM's structured output fails DTO validation."""


class LLMRateLimited(LLMError):
    """Raised after all tenacity retries exhaust on a 429 response."""

    def __init__(
        self,
        message: str = "LLM rate limit exceeded after retries",
        *,
        retry_after_ms: int | None = None,
        request_id: str | None = None,
    ) -> None:
        """Capture optional provider debug payload.

        :param message: Human-readable description, logged as-is.
        :param retry_after_ms: Server-suggested backoff in ms, if any.
        :param request_id: Provider request identifier for log
            correlation, if any.
        """
        super().__init__(message)
        self.retry_after_ms = retry_after_ms
        self.request_id = request_id


class LLMAuthFailed(LLMError):
    """Raised when the provider rejects credentials (401 or 403)."""


class LLMUnreachable(LLMError):
    """Raised on transport failure after tenacity retries."""


class LLMContextTooLarge(LLMError):
    """Raised when the payload exceeds the model's context window."""

    def __init__(
        self,
        message: str = "LLM context window exceeded",
        *,
        tokens: int | None = None,
        limit: int | None = None,
    ) -> None:
        """Capture optional token counts.

        :param message: Human-readable description, logged as-is.
        :param tokens: Measured payload tokens, if the provider
            reports them.
        :param limit: Model context-window limit, if known.
        """
        super().__init__(message)
        self.tokens = tokens
        self.limit = limit


class LLMRequestRejected(LLMError):
    """Raised on permanent 4xx that is not auth or context-size."""


class SourceError(DojoError):
    """Base class for Source read/fetch failures.

    Route handlers catch this base to render a single "couldn't load
    source" partial; specific subclasses preserve the detail needed
    by logging and retry decisions.
    """


class SourceNotFound(SourceError):
    """Raised when a FILE path does not exist."""


class SourceUnreadable(SourceError):
    """Raised when a FILE path cannot be read as UTF-8 text."""


class SourceFetchFailed(SourceError):
    """Raised on URL fetch failure (non-2xx, timeout, transport)."""

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Capture optional URL and HTTP status code.

        :param message: Human-readable description, logged as-is.
        :param url: Originating URL, if known.
        :param status_code: HTTP status on response-level failures
            (None on timeout/connection errors).
        """
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class SourceNotArticle(SourceError):
    """Raised when extraction yields no usable article text."""


class RepositoryRowCorrupt(DojoError):
    """Raised by mapper `*_from_row` on corrupted persisted data.

    Wraps stdlib exceptions (`ValueError` on bad UUID/enum,
    `json.JSONDecodeError` on bad JSON-encoded columns) so repository
    callers see a single `DojoError` subclass instead of low-level
    stdlib exceptions leaking through the persistence boundary.
    """

    def __init__(
        self,
        table: str,
        row_id: str,
        field: str,
        value: str,
    ) -> None:
        """Capture the offending table, row, field, and value.

        :param table: SQL table name (e.g. ``sources``).
        :param row_id: Primary key of the offending row.
        :param field: Column name whose value failed to parse.
        :param value: Repr of the offending raw value.
        """
        super().__init__(
            f"{table}[{row_id}].{field} has invalid value: {value!r}"
        )
        self.table = table
        self.row_id = row_id
        self.field = field
        self.value = value
