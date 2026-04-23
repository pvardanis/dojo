# ABOUTME: GenerateFromSource — TOPIC direct, other kinds via registry.
# ABOUTME: Non-TOPIC dispatch resolves through SourceTextExtractorRegistry.
"""GenerateFromSource use case."""

from __future__ import annotations

import uuid

from app.application.dtos import (
    DraftBundle,
    GenerateRequest,
    GenerateResponse,
)
from app.application.extractor_registry import (
    SourceTextExtractorRegistry,
)
from app.application.ports import DraftStore, DraftToken, LLMProvider
from app.domain.value_objects import SourceKind


class GenerateFromSource:
    """Generate a draft note + cards from a source, store under token."""

    def __init__(
        self,
        llm: LLMProvider,
        draft_store: DraftStore,
        extractor_registry: SourceTextExtractorRegistry,
    ) -> None:
        """Wire the use case against its ports."""
        self._llm = llm
        self._draft_store = draft_store
        self._extractors = extractor_registry

    def execute(self, request: GenerateRequest) -> GenerateResponse:
        """Dispatch on kind; TOPIC bypasses the extractor registry."""
        source_text: str | None = (
            None
            if request.kind is SourceKind.TOPIC
            else self._extract_source_text(request)
        )
        note, cards = self._llm.generate_note_and_cards(
            source_text=source_text,
            user_prompt=request.user_prompt,
        )
        bundle = DraftBundle(note=note, cards=cards)
        token = DraftToken(uuid.uuid4())
        self._draft_store.put(token, bundle)
        return GenerateResponse(token=token, bundle=bundle)

    def _extract_source_text(self, request: GenerateRequest) -> str:
        """Resolve the extractor for the kind and call it with the request."""
        extractor = self._extractors.get(request.kind)
        return extractor(request)
