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

from app.settings import get_settings


@pytest.mark.asyncio
async def test_alembic_upgrade_creates_version_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`alembic upgrade head` creates `alembic_version` on fresh DB.

    Uses a tmp-file sqlite DB independent of the session fixture
    stack so the test exercises the entire Alembic pipeline from
    cold: new URL -> set_main_option -> run_async_migrations.

    env.py reads `get_settings().database_url` and overrides the
    Config URL — so we monkeypatch `DATABASE_URL` and clear the
    settings lru_cache so env.py targets the tmp DB, not the default.
    """
    db_path = tmp_path / "dojo.alembic_smoke.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()

    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        # Wrap the sync Alembic CLI in a thread to avoid clashing
        # with pytest-asyncio's running loop (New Pitfall 5).
        await asyncio.to_thread(command.upgrade, cfg, "head")

        # Inspect the resulting DB for alembic_version.
        engine = create_async_engine(db_url)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
                tables = {row[0] for row in result}
        finally:
            await engine.dispose()

        assert "alembic_version" in tables, tables
    finally:
        get_settings.cache_clear()
