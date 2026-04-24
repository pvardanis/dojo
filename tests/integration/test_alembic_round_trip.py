# ABOUTME: Alembic upgrade → downgrade → upgrade round-trip.
# ABOUTME: Defends 0002 against SQLite-specific ALTER TABLE regressions.
"""Alembic round-trip test (CONTEXT D-08, VALIDATION.md dim 9)."""

from __future__ import annotations

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine


def test_upgrade_downgrade_upgrade_cycle(
    _migrated_engine: Engine,
    test_db_url: str,
    _alembic_cfg: AlembicConfig,
) -> None:
    """alembic head → base → head succeeds; 4 tables present.

    Requesting `_migrated_engine` guarantees the session-scoped
    `upgrade head` ran before this test body executes. The test
    confirms the four Phase 3 tables exist, cycles the schema back
    to base, asserts the tables drop, then restores head so later
    tests still see the migrated schema. The restore-at-end keeps
    this test order-independent.
    """
    engine = create_engine(test_db_url, future=True)
    try:
        try:
            tables = set(inspect(engine).get_table_names())
            assert {"sources", "notes", "cards", "card_reviews"} <= tables

            command.downgrade(_alembic_cfg, "base")
            tables = set(inspect(engine).get_table_names())
            assert "sources" not in tables
            assert "notes" not in tables
            assert "cards" not in tables
            assert "card_reviews" not in tables

            command.upgrade(_alembic_cfg, "head")
            tables = set(inspect(engine).get_table_names())
            assert {"sources", "notes", "cards", "card_reviews"} <= tables
        finally:
            # Always restore to head, even on assertion/command failure,
            # so the session-scoped `_migrated_engine` stays usable for
            # every later DB test in the run.
            command.upgrade(_alembic_cfg, "head")
    finally:
        engine.dispose()
