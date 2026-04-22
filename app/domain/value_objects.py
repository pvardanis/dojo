# ABOUTME: Domain value objects — SourceKind/Rating StrEnums + typed IDs.
# ABOUTME: StrEnum serializes natively; NewType aliases over uuid.UUID.
"""Domain value objects and typed IDs."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import NewType


class SourceKind(StrEnum):
    """Kind of source material a generation request targets."""

    FILE = "file"
    URL = "url"
    TOPIC = "topic"


class Rating(StrEnum):
    """User rating applied to a drilled card."""

    CORRECT = "correct"
    INCORRECT = "incorrect"


SourceId = NewType("SourceId", uuid.UUID)
NoteId = NewType("NoteId", uuid.UUID)
CardId = NewType("CardId", uuid.UUID)
ReviewId = NewType("ReviewId", uuid.UUID)
