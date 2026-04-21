# ABOUTME: SC #3 gate — alembic upgrade head creates alembic_version.
# ABOUTME: Persists the migration-pipeline smoke inside make check.
"""Alembic migration pipeline smoke test."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_alembic_upgrade_creates_version_table(
    tmp_path: Path,
) -> None:
    """`alembic upgrade head` creates `alembic_version` on fresh DB.

    Uses a tmp-file sqlite DB independent of the session fixture
    stack so the test exercises the entire Alembic pipeline from
    cold: new URL -> set_main_option -> run_async_migrations.
    env.py respects a caller-set URL (only the ini placeholder falls
    through to the settings singleton), so no DATABASE_URL monkeypatch
    or get_settings.cache_clear is required.
    """
    db_path = tmp_path / "dojo.alembic_smoke.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)

    # Wrap the sync Alembic CLI in a thread to avoid clashing
    # with pytest-asyncio's running loop (New Pitfall 5).
    await asyncio.to_thread(command.upgrade, cfg, "head")

    # Inspect the resulting DB: table exists AND revision pointer
    # advanced to the expected head. Asserting only the table exists
    # would pass even if Alembic created the table and then aborted
    # before running any revisions.
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            tables_result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = {row[0] for row in tables_result}
            assert "alembic_version" in tables, tables

            version_result = await conn.execute(
                text("SELECT version_num FROM alembic_version")
            )
            version = version_result.scalar_one()
            assert version == "0001", version
    finally:
        await engine.dispose()
