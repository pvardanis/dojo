# ABOUTME: GenerateFromSource non-TOPIC tests — registry hit and miss.
# ABOUTME: Empty registry raises UnsupportedSourceKind; hit runs extractor.
"""GenerateFromSource FILE/URL dispatch tests."""

from __future__ import annotations

import pytest

from app.application.dtos import GenerateRequest
from app.application.exceptions import UnsupportedSourceKind
from app.application.extractor_registry import (
    SourceTextExtractorRegistry,
)
from app.application.use_cases.generate_from_source import (
    GenerateFromSource,
)
from app.domain.value_objects import SourceKind
from tests.fakes import FakeDraftStore, FakeLLMProvider


def _build_use_case(
    llm: FakeLLMProvider | None = None,
    extractors: SourceTextExtractorRegistry | None = None,
) -> GenerateFromSource:
    """Assemble the use case with an empty registry by default."""
    return GenerateFromSource(
        llm=llm or FakeLLMProvider(),
        draft_store=FakeDraftStore(),
        extractor_registry=extractors or SourceTextExtractorRegistry(),
    )


def test_file_kind_without_registered_extractor_raises() -> None:
    """Empty registry + FILE kind surfaces UnsupportedSourceKind."""
    use_case = _build_use_case()
    with pytest.raises(UnsupportedSourceKind, match="file"):
        use_case.execute(
            GenerateRequest(
                kind=SourceKind.FILE,
                input="/tmp/x.md",
                user_prompt="p",
            )
        )


def test_url_kind_without_registered_extractor_raises() -> None:
    """Empty registry + URL kind surfaces UnsupportedSourceKind."""
    use_case = _build_use_case()
    with pytest.raises(UnsupportedSourceKind, match="url"):
        use_case.execute(
            GenerateRequest(
                kind=SourceKind.URL,
                input="https://example.com",
                user_prompt="p",
            )
        )


def test_unsupported_kind_short_circuits_before_the_llm() -> None:
    """Registry miss must raise before any LLM call is issued."""
    fake_llm = FakeLLMProvider()
    use_case = _build_use_case(llm=fake_llm)
    with pytest.raises(UnsupportedSourceKind):
        use_case.execute(
            GenerateRequest(
                kind=SourceKind.URL,
                input="https://example.com",
                user_prompt="p",
            )
        )
    assert fake_llm.calls_with == []


def test_file_kind_with_registered_extractor_passes_text_to_llm() -> None:
    """A registered FILE extractor runs and its output reaches the LLM."""
    captured_requests: list[GenerateRequest] = []

    def fake_file_extractor(request: GenerateRequest) -> str:
        captured_requests.append(request)
        return "extracted body"

    registry = SourceTextExtractorRegistry(
        {SourceKind.FILE: fake_file_extractor}
    )
    fake_llm = FakeLLMProvider()
    use_case = _build_use_case(llm=fake_llm, extractors=registry)
    request = GenerateRequest(
        kind=SourceKind.FILE, input="/tmp/x.md", user_prompt="p"
    )

    response = use_case.execute(request)

    assert captured_requests == [request]
    assert fake_llm.calls_with == [("extracted body", "p")]
    assert response.bundle.note == fake_llm.next_response[0]
