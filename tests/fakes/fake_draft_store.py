# ABOUTME: FakeDraftStore — dict wrapper with force_expire test hook.
# ABOUTME: put writes; pop is atomic read-and-delete (dict.pop).
"""FakeDraftStore — hand-written fake for DraftStore port."""

from __future__ import annotations

from app.application.dtos import DraftBundle
from app.application.ports import DraftToken


class FakeDraftStore:
    """In-memory dict with an atomic pop and a force_expire hook."""

    def __init__(self) -> None:
        """Start with empty store + empty put log."""
        self._store: dict[DraftToken, DraftBundle] = {}
        self.puts: list[tuple[DraftToken, DraftBundle]] = []

    def put(self, token: DraftToken, bundle: DraftBundle) -> None:
        """Store the bundle and record the call."""
        self._store[token] = bundle
        self.puts.append((token, bundle))

    def pop(self, token: DraftToken) -> DraftBundle | None:
        """Atomic read-and-delete; returns None if missing or expired."""
        return self._store.pop(token, None)

    def force_expire(self, token: DraftToken) -> None:
        """Test hook: drop token as if its TTL had expired."""
        self._store.pop(token, None)
