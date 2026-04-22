# ABOUTME: Domain value objects — SourceKind, Rating enums + typed IDs.
# ABOUTME: NewType aliases over uuid.UUID; zero runtime cost.
"""Domain value objects and typed IDs."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import NewType


class SourceKind(Enum):
    """Kind of source material a generation request targets."""

    FILE = "file"
    URL = "url"
    TOPIC = "topic"


class Rating(Enum):
    """User rating applied to a drilled card."""

    CORRECT = "correct"
    INCORRECT = "incorrect"


SourceId = NewType("SourceId", uuid.UUID)
NoteId = NewType("NoteId", uuid.UUID)
CardId = NewType("CardId", uuid.UUID)
ReviewId = NewType("ReviewId", uuid.UUID)
