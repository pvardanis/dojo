# ABOUTME: GenerateFromSource use case — TOPIC branch wired in Phase 2.
# ABOUTME: FILE + URL branches raise UnsupportedSourceKind until Phase 4.
"""GenerateFromSource use case."""

from __future__ import annotations

import uuid

from app.application.dtos import (
    DraftBundle,
    GenerateRequest,
    GenerateResponse,
)
from app.application.exceptions import UnsupportedSourceKind
from app.application.ports import DraftStore, DraftToken, LLMProvider
from app.domain.value_objects import SourceKind


class GenerateFromSource:
    """Generate a draft note + cards from a source, store under token."""

    def __init__(
        self,
        llm: LLMProvider,
        draft_store: DraftStore,
    ) -> None:
        """Wire the use case against its ports."""
        self._llm = llm
        self._draft_store = draft_store

    def execute(self, request: GenerateRequest) -> GenerateResponse:
        """Dispatch on kind; TOPIC fully wired, FILE/URL raise."""
        if request.kind is SourceKind.TOPIC:
            note, cards = self._llm.generate_note_and_cards(
                source_text=None,
                user_prompt=request.user_prompt,
            )
            bundle = DraftBundle(note=note, cards=cards)
            token = DraftToken(uuid.uuid4())
            self._draft_store.put(token, bundle)
            return GenerateResponse(token=token, bundle=bundle)

        raise UnsupportedSourceKind(
            f"Source kind {request.kind.value!r} not supported yet"
        )
