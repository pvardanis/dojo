# ABOUTME: GenerateFromSource unsupported-kind tests — FILE/URL raise.
# ABOUTME: Phase 4 replaces these branches with SourceReader + UrlFetcher.
"""GenerateFromSource FILE/URL unsupported-kind tests."""

from __future__ import annotations

import pytest

from app.application.dtos import GenerateRequest
from app.application.exceptions import UnsupportedSourceKind
from app.application.use_cases.generate_from_source import (
    GenerateFromSource,
)
from app.domain.value_objects import SourceKind
from tests.fakes import FakeDraftStore, FakeLLMProvider


def test_generate_file_kind_raises_unsupported_source_kind() -> None:
    """FILE kind raises in Phase 2; Phase 4 adds SourceReader wiring."""
    use_case = GenerateFromSource(
        llm=FakeLLMProvider(), draft_store=FakeDraftStore()
    )
    with pytest.raises(UnsupportedSourceKind, match="file"):
        use_case.execute(
            GenerateRequest(
                kind=SourceKind.FILE,
                input="/tmp/x.md",
                user_prompt="p",
            )
        )


def test_generate_url_kind_raises_unsupported_source_kind() -> None:
    """URL kind raises in Phase 2; Phase 4 adds UrlFetcher wiring."""
    use_case = GenerateFromSource(
        llm=FakeLLMProvider(), draft_store=FakeDraftStore()
    )
    with pytest.raises(UnsupportedSourceKind, match="url"):
        use_case.execute(
            GenerateRequest(
                kind=SourceKind.URL,
                input="https://example.com",
                user_prompt="p",
            )
        )


def test_generate_url_kind_does_not_call_llm() -> None:
    """Unsupported-kind branch short-circuits before touching the LLM."""
    fake_llm = FakeLLMProvider()
    use_case = GenerateFromSource(llm=fake_llm, draft_store=FakeDraftStore())
    with pytest.raises(UnsupportedSourceKind):
        use_case.execute(
            GenerateRequest(
                kind=SourceKind.URL,
                input="https://example.com",
                user_prompt="p",
            )
        )
    assert fake_llm.calls_with == []
