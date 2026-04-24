# ABOUTME: Application-layer exception hierarchy tests.
# ABOUTME: Every exception inherits from DojoError; messages round-trip.
"""Application exception tests."""

from __future__ import annotations

import pytest

from app.application.exceptions import (
    DraftExpired,
    ExtractorNotApplicable,
    LLMAuthFailed,
    LLMContextTooLarge,
    LLMError,
    LLMOutputMalformed,
    LLMRateLimited,
    LLMRequestRejected,
    LLMUnreachable,
    RepositoryRowCorrupt,
    SourceError,
    SourceFetchFailed,
    SourceNotArticle,
    SourceNotFound,
    SourceUnreadable,
    UnsupportedSourceKind,
)
from app.domain.exceptions import DojoError

_LLM_SUBCLASSES = [
    LLMOutputMalformed,
    LLMRateLimited,
    LLMAuthFailed,
    LLMUnreachable,
    LLMContextTooLarge,
    LLMRequestRejected,
]

_SOURCE_SUBCLASSES = [
    SourceNotFound,
    SourceUnreadable,
    SourceFetchFailed,
    SourceNotArticle,
]

_DOJO_DIRECT_SUBCLASSES = [
    UnsupportedSourceKind,
    ExtractorNotApplicable,
    DraftExpired,
    LLMError,
    SourceError,
    RepositoryRowCorrupt,
]


@pytest.mark.parametrize("cls", _LLM_SUBCLASSES)
def test_llm_subclasses_inherit_llm_error(
    cls: type[Exception],
) -> None:
    """Every LLM-* class sits under the LLMError category base."""
    assert issubclass(cls, LLMError)
    assert issubclass(cls, DojoError)


@pytest.mark.parametrize("cls", _SOURCE_SUBCLASSES)
def test_source_subclasses_inherit_source_error(
    cls: type[Exception],
) -> None:
    """Every Source* class sits under the SourceError category base."""
    assert issubclass(cls, SourceError)
    assert issubclass(cls, DojoError)


@pytest.mark.parametrize("cls", _DOJO_DIRECT_SUBCLASSES)
def test_dojo_direct_subclasses(cls: type[Exception]) -> None:
    """Uncategorised classes inherit DojoError directly."""
    assert issubclass(cls, DojoError)


def test_application_exception_carries_message() -> None:
    """Raising UnsupportedSourceKind preserves its message via str()."""
    with pytest.raises(UnsupportedSourceKind) as exc_info:
        raise UnsupportedSourceKind("x")
    assert str(exc_info.value) == "x"


def test_llm_rate_limited_structured_payload() -> None:
    """LLMRateLimited preserves retry_after_ms and request_id."""
    exc = LLMRateLimited(
        "rate limited",
        retry_after_ms=1500,
        request_id="req_abc",
    )
    assert str(exc) == "rate limited"
    assert exc.retry_after_ms == 1500
    assert exc.request_id == "req_abc"


def test_llm_rate_limited_default_attrs() -> None:
    """LLMRateLimited attrs default to None when not supplied."""
    exc = LLMRateLimited()
    assert exc.retry_after_ms is None
    assert exc.request_id is None


def test_llm_context_too_large_structured_payload() -> None:
    """LLMContextTooLarge preserves tokens and limit."""
    exc = LLMContextTooLarge(tokens=210_000, limit=200_000)
    assert exc.tokens == 210_000
    assert exc.limit == 200_000


def test_source_fetch_failed_structured_payload() -> None:
    """SourceFetchFailed preserves url and status_code."""
    exc = SourceFetchFailed(
        "403 Forbidden",
        url="https://example.com/a",
        status_code=403,
    )
    assert str(exc) == "403 Forbidden"
    assert exc.url == "https://example.com/a"
    assert exc.status_code == 403


def test_source_fetch_failed_accepts_message_only() -> None:
    """SourceFetchFailed still constructs from a bare message."""
    exc = SourceFetchFailed("timeout")
    assert str(exc) == "timeout"
    assert exc.url is None
    assert exc.status_code is None


def test_repository_row_corrupt_captures_context() -> None:
    """RepositoryRowCorrupt stores table/row_id/field/value."""
    exc = RepositoryRowCorrupt(
        table="sources",
        row_id="abc",
        field="kind",
        value="NOT_A_KIND",
    )
    assert exc.table == "sources"
    assert exc.row_id == "abc"
    assert exc.field == "kind"
    assert exc.value == "NOT_A_KIND"
    assert "sources[abc].kind" in str(exc)
    assert "'NOT_A_KIND'" in str(exc)


def test_repository_row_corrupt_is_dojo_error() -> None:
    """RepositoryRowCorrupt is a DojoError for catch-all handlers."""
    assert issubclass(RepositoryRowCorrupt, DojoError)
