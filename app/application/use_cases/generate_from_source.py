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
    """Generate a draft note + cards and hold them in-memory.

    **Nothing in this use case touches the database.** The generated
    note and card candidates are stored in a `DraftStore` under a
    minted `DraftToken` with a 30-minute TTL. A separate persistence
    use case (Phase 4) pops the draft from the store and writes
    `Source`, `Note`, and approved `Card`s in a single atomic
    transaction when — and only when — the user clicks Save. If the
    user abandons the draft, the TTL reclaims it; no orphan rows.
    """

    def __init__(
        self,
        llm: LLMProvider,
        draft_store: DraftStore,
        extractor_registry: SourceTextExtractorRegistry,
    ) -> None:
        """Wire the use case against its ports.

        No repository port, no database session: this use case is
        pre-persist. See the class docstring for the save/draft
        contract.

        :param llm: The LLM provider port used to generate the note and
            cards from the resolved `source_text` + `user_prompt`.
        :param draft_store: Port holding the pending draft bundle under
            its minted `DraftToken` until an explicit save use case
            commits or discards it.
        :param extractor_registry: Resolves non-TOPIC `SourceKind` to
            its extractor callable; never consulted for `TOPIC`.
        """
        self._llm = llm
        self._draft_store = draft_store
        self._extractors = extractor_registry

    def execute(self, request: GenerateRequest) -> GenerateResponse:
        """Run the generate flow and return the stored draft envelope.

        The returned `DraftBundle` is held in the `DraftStore` only;
        no database writes happen here. The Phase 4 save use case
        pops the draft by `DraftToken` and persists `Source`, `Note`,
        and approved `Card`s atomically.

        :param request: The incoming `GenerateRequest`; its `kind`
            drives dispatch, its `user_prompt` is forwarded to the
            LLM, and its `input` feeds the extractor for non-TOPIC
            kinds.
        :returns: A `GenerateResponse` holding the minted
            `DraftToken` and the stored `DraftBundle`.
        :raises ExtractorNotApplicable: If a non-TOPIC caller routes
            `TOPIC` through the registry (a programmer-error path).
        :raises UnsupportedSourceKind: If `request.kind` is a FILE /
            URL kind with no extractor registered (Phase 2 pre-wiring).
        """
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
        """Resolve the extractor for the kind and call it with the request.

        :param request: The non-TOPIC `GenerateRequest` whose kind
            keys into the extractor registry.
        :returns: The extracted source text to hand to the LLM.
        """
        extractor = self._extractors.get(request.kind)
        return extractor(request)
