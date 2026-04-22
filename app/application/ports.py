# ABOUTME: Application ports — Protocols, Callable aliases, NewTypes.
# ABOUTME: Full surface lands in Unit 3; Unit 2 declares DraftToken only.
"""Application ports (partial — full Protocol surface lands next)."""

from __future__ import annotations

import uuid
from typing import NewType

DraftToken = NewType("DraftToken", uuid.UUID)
