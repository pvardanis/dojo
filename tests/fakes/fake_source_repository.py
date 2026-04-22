# ABOUTME: Dict-backed fake SourceRepository — exposes .saved state.
# ABOUTME: Tests assert against repo.saved[source_id], no call tracking.
"""FakeSourceRepository — dict-backed in-memory fake."""

from __future__ import annotations

from app.domain.entities import Source
from app.domain.value_objects import SourceId


class FakeSourceRepository:
    """In-memory dict of Source entities keyed by SourceId."""

    def __init__(self) -> None:
        """Start with empty store."""
        self.saved: dict[SourceId, Source] = {}

    def save(self, source: Source) -> None:
        """Insert or overwrite the source entry."""
        self.saved[source.id] = source

    def get(self, source_id: SourceId) -> Source | None:
        """Return the stored source or None if missing."""
        return self.saved.get(source_id)
