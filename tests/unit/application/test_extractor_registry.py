# ABOUTME: Tests for SourceTextExtractorRegistry lookup + miss errors.
# ABOUTME: TOPIC → ExtractorNotApplicable; others → UnsupportedSourceKind.
"""SourceTextExtractorRegistry unit tests."""

from __future__ import annotations

import pytest

from app.application.dtos import GenerateRequest
from app.application.exceptions import (
    ExtractorNotApplicable,
    UnsupportedSourceKind,
)
from app.application.extractor_registry import (
    SourceTextExtractorRegistry,
)
from app.domain.value_objects import SourceKind


def _file_request(payload: str = "/tmp/x.md") -> GenerateRequest:
    """Build a FILE-kind GenerateRequest for extractor invocation."""
    return GenerateRequest(
        kind=SourceKind.FILE, input=payload, user_prompt="p"
    )


def test_registered_extractor_is_returned_by_get() -> None:
    """A kind mapped at construction resolves to its callable."""

    def fake_extractor(request: GenerateRequest) -> str:
        return f"extracted from {request.input}"

    registry = SourceTextExtractorRegistry({SourceKind.FILE: fake_extractor})

    extractor = registry.get(SourceKind.FILE)
    assert extractor(_file_request("p.md")) == "extracted from p.md"


def test_unregistered_kind_raises_unsupported_source_kind() -> None:
    """Absent keys surface `UnsupportedSourceKind` naming the kind."""
    registry = SourceTextExtractorRegistry()

    with pytest.raises(UnsupportedSourceKind, match="file"):
        registry.get(SourceKind.FILE)
    with pytest.raises(UnsupportedSourceKind, match="url"):
        registry.get(SourceKind.URL)


def test_topic_lookup_raises_extractor_not_applicable() -> None:
    """TOPIC has no extractor by design — lookup is a category mismatch."""
    registry = SourceTextExtractorRegistry()

    with pytest.raises(ExtractorNotApplicable, match="TOPIC"):
        registry.get(SourceKind.TOPIC)


def test_topic_error_is_not_unsupported_source_kind() -> None:
    """The TOPIC error is distinct from the "not wired yet" error type."""
    registry = SourceTextExtractorRegistry()

    with pytest.raises(ExtractorNotApplicable) as excinfo:
        registry.get(SourceKind.TOPIC)
    assert not isinstance(excinfo.value, UnsupportedSourceKind)
