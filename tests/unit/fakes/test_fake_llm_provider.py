# ABOUTME: FakeLLMProvider contract tests — call log + canned response.
# ABOUTME: Proves public .calls_with and .next_response attributes work.
"""FakeLLMProvider unit tests."""

from __future__ import annotations

from app.application.dtos import CardDTO, NoteDTO
from tests.fakes.fake_llm_provider import FakeLLMProvider


def test_returns_default_canned_note_and_cards() -> None:
    """Default canned response is a NoteDTO + one CardDTO."""
    fake = FakeLLMProvider()
    note, cards = fake.generate_note_and_cards(
        source_text=None, user_prompt="p"
    )
    assert note.title == "fake title"
    assert note.content_md == "fake body"
    assert len(cards) == 1


def test_calls_with_logs_every_call() -> None:
    """Every call is recorded on .calls_with in order."""
    fake = FakeLLMProvider()
    fake.generate_note_and_cards(source_text=None, user_prompt="a")
    fake.generate_note_and_cards(source_text="src", user_prompt="b")
    assert fake.calls_with == [(None, "a"), ("src", "b")]


def test_next_response_override_changes_return() -> None:
    """Mutating .next_response changes subsequent return values."""
    fake = FakeLLMProvider()
    fake.next_response = (
        NoteDTO(title="override", content_md="new body"),
        [CardDTO(question="Q", answer="A")],
    )
    note, cards = fake.generate_note_and_cards(
        source_text=None, user_prompt="p"
    )
    assert note.title == "override"
    assert cards[0].question == "Q"


def test_returns_tuple_of_note_dto_and_card_list() -> None:
    """Return shape is (NoteDTO, list[CardDTO])."""
    fake = FakeLLMProvider()
    note, cards = fake.generate_note_and_cards(
        source_text=None, user_prompt="p"
    )
    assert isinstance(note, NoteDTO)
    assert isinstance(cards, list)
    assert all(isinstance(c, CardDTO) for c in cards)
