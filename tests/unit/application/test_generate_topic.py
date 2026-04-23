# ABOUTME: GenerateFromSource TOPIC-branch tests — happy-path end-to-end.
# ABOUTME: Covers LLM call shape, bundle contents, draft-store round-trip.
"""GenerateFromSource TOPIC-path tests."""

from __future__ import annotations

import uuid

from app.application.dtos import GenerateRequest
from app.application.extractor_registry import (
    SourceTextExtractorRegistry,
)
from app.application.ports import DraftToken
from app.application.use_cases.generate_from_source import (
    GenerateFromSource,
)
from app.domain.value_objects import SourceKind
from tests.fakes import FakeDraftStore, FakeLLMProvider


class _SpyExtractorRegistry(SourceTextExtractorRegistry):
    """Spy variant that records every `get` call for bypass assertions."""

    def __init__(self) -> None:
        """Start empty and attach an empty call log."""
        super().__init__()
        self.get_calls: list[SourceKind] = []

    def get(self, key: SourceKind):  # type: ignore[override]
        """Record the lookup key before delegating to the base registry."""
        self.get_calls.append(key)
        return super().get(key)


def _topic_request(prompt: str = "alpha") -> GenerateRequest:
    """Build a TOPIC GenerateRequest with no source input."""
    return GenerateRequest(
        kind=SourceKind.TOPIC, input=None, user_prompt=prompt
    )


def _build_use_case(
    llm: FakeLLMProvider | None = None,
    draft_store: FakeDraftStore | None = None,
    extractors: SourceTextExtractorRegistry | None = None,
) -> GenerateFromSource:
    """Assemble the use case with empty-registry defaults for TOPIC tests."""
    return GenerateFromSource(
        llm=llm or FakeLLMProvider(),
        draft_store=draft_store or FakeDraftStore(),
        extractor_registry=extractors or SourceTextExtractorRegistry(),
    )


def test_generate_from_topic_returns_response_with_token_and_bundle() -> None:
    """TOPIC path returns a DraftToken plus a bundle with LLM output."""
    fake_llm = FakeLLMProvider()
    use_case = _build_use_case(llm=fake_llm)
    expected_note, expected_cards = fake_llm.next_response

    response = use_case.execute(_topic_request())

    assert isinstance(response.token, uuid.UUID)
    assert response.token == DraftToken(response.token)
    assert response.bundle.note == expected_note
    assert response.bundle.cards == expected_cards


def test_generate_from_topic_calls_llm_with_none_source_text() -> None:
    """TOPIC path passes source_text=None and the prompt to the LLM port."""
    fake_llm = FakeLLMProvider()
    use_case = _build_use_case(llm=fake_llm)

    use_case.execute(_topic_request("alpha"))

    assert fake_llm.calls_with == [(None, "alpha")]


def test_generate_from_topic_stores_bundle_in_draft_store() -> None:
    """TOPIC path puts (token, bundle) into the draft store exactly once."""
    fake_store = FakeDraftStore()
    use_case = _build_use_case(draft_store=fake_store)

    response = use_case.execute(_topic_request())

    assert fake_store.puts == [(response.token, response.bundle)]


def test_generate_bundle_round_trips_through_draft_store_pop() -> None:
    """Bundle put into store is returned by the subsequent pop; atomic."""
    fake_store = FakeDraftStore()
    use_case = _build_use_case(draft_store=fake_store)

    response = use_case.execute(_topic_request())

    assert fake_store.pop(response.token) == response.bundle
    assert fake_store.pop(response.token) is None


def test_topic_path_never_queries_the_extractor_registry() -> None:
    """TOPIC is extraction-free; the registry must not be consulted."""
    spy = _SpyExtractorRegistry()
    use_case = _build_use_case(extractors=spy)

    use_case.execute(_topic_request())

    assert spy.get_calls == []
