# ABOUTME: Proves every fake structurally subtypes its Protocol.
# ABOUTME: Runtime: hasattr checks. Typecheck: annotated assignments.
"""Structural-subtype smoke tests for hand-written fakes."""

from __future__ import annotations

from app.application.ports import (
    CardRepository,
    CardReviewRepository,
    DraftStore,
    LLMProvider,
    NoteRepository,
    SourceRepository,
)
from tests.fakes import (
    FakeCardRepository,
    FakeCardReviewRepository,
    FakeDraftStore,
    FakeLLMProvider,
    FakeNoteRepository,
    FakeSourceRepository,
)


def test_fakes_have_required_public_methods() -> None:
    """Each fake exposes the public methods its Protocol declares."""
    assert hasattr(FakeLLMProvider(), "generate_note_and_cards")
    assert hasattr(FakeSourceRepository(), "save")
    assert hasattr(FakeSourceRepository(), "get")
    assert hasattr(FakeNoteRepository(), "save")
    assert hasattr(FakeNoteRepository(), "get")
    assert hasattr(FakeCardRepository(), "save")
    assert hasattr(FakeCardRepository(), "get")
    assert hasattr(FakeCardReviewRepository(), "save")
    assert hasattr(FakeDraftStore(), "put")
    assert hasattr(FakeDraftStore(), "pop")


def test_fakes_are_assignable_to_their_protocols() -> None:
    """Structural-subtype check — ty validates the annotated vars."""
    llm: LLMProvider = FakeLLMProvider()
    sources: SourceRepository = FakeSourceRepository()
    notes: NoteRepository = FakeNoteRepository()
    cards: CardRepository = FakeCardRepository()
    reviews: CardReviewRepository = FakeCardReviewRepository()
    drafts: DraftStore = FakeDraftStore()
    assert llm is not None
    assert sources is not None
    assert notes is not None
    assert cards is not None
    assert reviews is not None
    assert drafts is not None
