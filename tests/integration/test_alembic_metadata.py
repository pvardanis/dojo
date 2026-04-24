# ABOUTME: Smoke test — Base.metadata sees the four Phase 3 tables.
# ABOUTME: Catches PITFALL M9 "env.py imports Base but not models.py".
"""Alembic metadata smoke test (RESEARCH R5)."""

from __future__ import annotations

from app.infrastructure.db import models as _models  # noqa: F401
from app.infrastructure.db.session import Base


def test_base_metadata_has_four_phase_3_tables() -> None:
    """Importing models registers sources/notes/cards/card_reviews."""
    assert set(Base.metadata.tables) == {
        "sources",
        "notes",
        "cards",
        "card_reviews",
    }
