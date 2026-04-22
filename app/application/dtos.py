# ABOUTME: Pydantic DTOs for LLM I/O + stdlib dataclasses for use cases.
# ABOUTME: extra="ignore" + min_length=1 per CONTEXT Pydantic posture.
"""Application DTOs — LLM boundary + internal use-case types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.domain.value_objects import SourceKind

if TYPE_CHECKING:
    from app.application.ports import DraftToken


class NoteDTO(BaseModel):
    """Structured note output from the LLM provider."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1)
    content_md: str = Field(min_length=1)


class CardDTO(BaseModel):
    """One Q&A card produced by the LLM provider."""

    model_config = ConfigDict(extra="ignore")

    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    tags: tuple[str, ...] = ()


class GeneratedContent(BaseModel):
    """LLM tool-use envelope holding a note plus at least one card."""

    model_config = ConfigDict(extra="ignore")

    note: NoteDTO
    cards: list[CardDTO] = Field(min_length=1)


@dataclass(frozen=True)
class DraftBundle:
    """Proposed note + cards held in the draft store pre-save."""

    note: NoteDTO
    cards: list[CardDTO]


@dataclass(frozen=True)
class GenerateRequest:
    """Request to `GenerateFromSource.execute` (TOPIC has input=None)."""

    kind: SourceKind
    input: str | None
    user_prompt: str


@dataclass(frozen=True)
class GenerateResponse:
    """Response envelope carrying the draft token plus its bundle."""

    token: DraftToken
    bundle: DraftBundle
