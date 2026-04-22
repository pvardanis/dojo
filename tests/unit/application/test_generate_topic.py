# ABOUTME: GenerateFromSource TOPIC-branch tests — happy-path end-to-end.
# ABOUTME: Covers LLM call shape, bundle contents, draft-store round-trip.
"""GenerateFromSource TOPIC-path tests."""

from __future__ import annotations

import uuid

from app.application.dtos import GenerateRequest
from app.application.ports import DraftToken
from app.application.use_cases.generate_from_source import (
    GenerateFromSource,
)
from app.domain.value_objects import SourceKind
from tests.fakes import FakeDraftStore, FakeLLMProvider


def _topic_request(prompt: str = "alpha") -> GenerateRequest:
    """Build a TOPIC GenerateRequest with no source input."""
    return GenerateRequest(
        kind=SourceKind.TOPIC, input=None, user_prompt=prompt
    )


def test_generate_from_topic_returns_response_with_token_and_bundle() -> None:
    """TOPIC path returns a DraftToken plus a bundle with LLM output."""
    fake_llm = FakeLLMProvider()
    use_case = GenerateFromSource(llm=fake_llm, draft_store=FakeDraftStore())
    expected_note, expected_cards = fake_llm.next_response

    response = use_case.execute(_topic_request())

    assert isinstance(response.token, uuid.UUID)
    assert response.token == DraftToken(response.token)
    assert response.bundle.note == expected_note
    assert response.bundle.cards == expected_cards


def test_generate_from_topic_calls_llm_with_none_source_text() -> None:
    """TOPIC path passes source_text=None and the prompt to the LLM port."""
    fake_llm = FakeLLMProvider()
    use_case = GenerateFromSource(llm=fake_llm, draft_store=FakeDraftStore())

    use_case.execute(_topic_request("alpha"))

    assert fake_llm.calls_with == [(None, "alpha")]


def test_generate_from_topic_stores_bundle_in_draft_store() -> None:
    """TOPIC path puts (token, bundle) into the draft store exactly once."""
    fake_store = FakeDraftStore()
    use_case = GenerateFromSource(
        llm=FakeLLMProvider(), draft_store=fake_store
    )

    response = use_case.execute(_topic_request())

    assert fake_store.puts == [(response.token, response.bundle)]


def test_generate_bundle_round_trips_through_draft_store_pop() -> None:
    """Bundle put into store is returned by the subsequent pop; atomic."""
    fake_store = FakeDraftStore()
    use_case = GenerateFromSource(
        llm=FakeLLMProvider(), draft_store=fake_store
    )

    response = use_case.execute(_topic_request())

    assert fake_store.pop(response.token) == response.bundle
    assert fake_store.pop(response.token) is None
