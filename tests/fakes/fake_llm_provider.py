# ABOUTME: Hand-written fake LLMProvider for Phase 2 use-case tests.
# ABOUTME: Records calls on .calls_with; canned response overridable.
"""FakeLLMProvider — structural subtype of LLMProvider."""

from __future__ import annotations

from app.application.dtos import CardDTO, NoteDTO


class FakeLLMProvider:
    """Records calls and returns a canned NoteDTO + cards list."""

    def __init__(self) -> None:
        """Start with empty call log + default canned response."""
        self.calls_with: list[tuple[str | None, str]] = []
        self.next_response: tuple[NoteDTO, list[CardDTO]] = (
            NoteDTO(title="fake title", content_md="fake body"),
            [CardDTO(question="q?", answer="a.")],
        )

    def generate_note_and_cards(
        self, source_text: str | None, user_prompt: str
    ) -> tuple[NoteDTO, list[CardDTO]]:
        """Record the call and return the current canned response."""
        self.calls_with.append((source_text, user_prompt))
        return self.next_response
