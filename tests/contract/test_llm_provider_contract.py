# ABOUTME: TEST-03 contract harness — asserts Protocol shape for LLM port.
# ABOUTME: Fake leg always runs; anthropic leg auto-skips (env + import).
"""LLMProvider contract tests — shared across fake and real impls."""

from __future__ import annotations

import os

import pytest

from app.application.dtos import CardDTO, NoteDTO
from tests.fakes import FakeLLMProvider


@pytest.fixture(params=["fake", "anthropic"])
def llm_provider(request: pytest.FixtureRequest):
    """Yield a fake or real LLMProvider; real skips without opt-in."""
    if request.param == "fake":
        yield FakeLLMProvider()
        return

    if os.getenv("RUN_LLM_TESTS", "").lower() not in ("1", "true", "yes"):
        pytest.skip("RUN_LLM_TESTS not set")
    adapter_module = pytest.importorskip(
        "app.infrastructure.llm.anthropic_provider"
    )
    yield adapter_module.AnthropicLLMProvider()


def test_generate_returns_note_and_card_list(llm_provider) -> None:
    """Return type is (NoteDTO, list[CardDTO]) with non-empty cards."""
    note, cards = llm_provider.generate_note_and_cards(
        source_text=None, user_prompt="alpha"
    )
    assert isinstance(note, NoteDTO)
    assert isinstance(cards, list)
    assert len(cards) >= 1
    assert all(isinstance(c, CardDTO) for c in cards)
