# ABOUTME: SC #3 gate — alembic upgrade head creates alembic_version.
# ABOUTME: Persists the migration-pipeline smoke inside make check.
"""Alembic migration pipeline smoke test."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text


def test_alembic_upgrade_creates_version_table(tmp_path: Path) -> None:
    """`alembic upgrade head` creates `alembic_version` on fresh DB.

    Uses a tmp-file sqlite DB independent of the session fixture
    stack so the test exercises the entire Alembic pipeline from
    cold: new URL -> set_main_option -> run_migrations_online.
    env.py respects a caller-set URL (only the ini placeholder falls
    through to the settings singleton).
    """
    db_path = tmp_path / "dojo.alembic_smoke.db"
    db_url = f"sqlite:///{db_path}"

    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")

    # Inspect the resulting DB: table exists AND revision pointer
    # advanced to the expected head. Asserting only the table exists
    # would pass even if Alembic created the table and then aborted
    # before running any revisions.
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            tables_result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = {row[0] for row in tables_result}
            assert "alembic_version" in tables, tables

            version_result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            )
            version = version_result.scalar_one()
            assert version == "0002", version
    finally:
        engine.dispose()
