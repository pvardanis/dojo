# ABOUTME: Anthropic tool-use response parser + Pydantic DTO validation.
# ABOUTME: Raises LLMOutputMalformed on missing tool_use; VE on DTO fail.
"""Anthropic tool-use response parser."""

from __future__ import annotations

from typing import Any

from app.application.dtos import CardDTO, GeneratedContent, NoteDTO
from app.application.exceptions import LLMOutputMalformed


def parse_and_validate(
    response: Any,
) -> tuple[NoteDTO, list[CardDTO]]:
    """Extract the tool_use block and validate via Pydantic.

    :param response: The anthropic SDK response object.
    :returns: `(NoteDTO, list[CardDTO])` parsed from tool-use input.
    :raises LLMOutputMalformed: When no tool_use block is present.
    :raises pydantic.ValidationError: When payload fails DTO
        validation; caught upstream to trigger semantic retry.
    """
    tool_blocks = [b for b in response.content if b.type == "tool_use"]
    if not tool_blocks:
        raise LLMOutputMalformed("no tool_use block in response")
    validated = GeneratedContent.model_validate(tool_blocks[0].input)
    return validated.note, validated.cards
