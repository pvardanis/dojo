# ABOUTME: SC #4 canary — async session + real Alembic migrations.
# ABOUTME: Must pass 10x in a row via `pytest --count=10`.
"""First integration test — proves the fixture stack end-to-end."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_async_session_executes_trivial_query(
    session: AsyncSession,
) -> None:
    """Open a session, SELECT 1, close cleanly."""
    result = await session.execute(text("SELECT 1"))
    value = result.scalar_one()
    assert value == 1
