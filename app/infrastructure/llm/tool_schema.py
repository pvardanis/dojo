# ABOUTME: Anthropic tool-use schema for generate_note_and_cards.
# ABOUTME: strict=True + additionalProperties=false grammar-constrains output.
"""Tool-use schema constant.

Hand-written rather than derived from ``NoteDTO.model_json_schema()``
because Anthropic's tool-use schema validator rejects ``$ref`` /
``$defs`` that Pydantic emits for nested models (RESEARCH §B.2 / R2).
Any future ``NoteDTO`` / ``CardDTO`` field addition must be mirrored
here by hand, and a regression test should pin the field list.
"""

from __future__ import annotations

from typing import Any

TOOL_DEFINITION: dict[str, Any] = {
    "name": "generate_note_and_cards",
    "description": (
        "Produce a study note and a list of Q&A cards from the "
        "provided source text and user prompt. Return EXACTLY ONE "
        "tool_use call; do not emit free-form text."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "note": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "content_md": {"type": "string"},
                },
                "required": ["title", "content_md"],
            },
            "cards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["question", "answer", "tags"],
                },
            },
        },
        "required": ["note", "cards"],
    },
}
