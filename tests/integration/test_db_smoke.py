# ABOUTME: SC #4 canary — sync session + real Alembic migrations.
# ABOUTME: Must pass 10x in a row via `pytest --count=10`.
"""First integration test — proves the fixture stack end-to-end."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def test_session_executes_trivial_query(session: Session) -> None:
    """Open a session, SELECT 1, close cleanly."""
    result = session.execute(text("SELECT 1"))
    value = result.scalar_one()
    assert value == 1
