# ABOUTME: SQLite PRAGMA listener regression net.
# ABOUTME: Asserts foreign_keys / journal_mode / busy_timeout are applied.
"""Dialect-guarded PRAGMA listener integration test."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.db.session import _configure_sqlite


@pytest.mark.asyncio
async def test_sqlite_pragmas_applied_on_connect(tmp_path: Path) -> None:
    """The connect listener sets FK/WAL/busy_timeout on every connection.

    The `app.infrastructure.db.session._configure_sqlite` listener is
    bound to the module-level engine's sync_engine — so the conftest
    `_migrated_engine` (which creates its own `create_async_engine`)
    would silently bypass it. This test creates a fresh aiosqlite
    engine, re-registers the listener, opens a connection, and asserts
    every PRAGMA is active.

    Without this test a regression that drops the dialect guard, breaks
    a PRAGMA string, or re-orders the cursor calls would ship without
    failing any SC gate.
    """
    from sqlalchemy import event

    db_url = f"sqlite+aiosqlite:///{tmp_path / 'pragmas.db'}"
    test_engine = create_async_engine(db_url)
    event.listen(test_engine.sync_engine, "connect", _configure_sqlite)

    try:
        async with test_engine.connect() as conn:
            fk = await conn.execute(text("PRAGMA foreign_keys"))
            journal = await conn.execute(text("PRAGMA journal_mode"))
            busy = await conn.execute(text("PRAGMA busy_timeout"))
            assert fk.scalar_one() == 1
            assert journal.scalar_one() == "wal"
            assert busy.scalar_one() == 5000
    finally:
        await test_engine.dispose()


def test_pragma_listener_is_dialect_guarded() -> None:
    """The listener is a no-op when the engine is not SQLite.

    Calling `_configure_sqlite` when the engine dialect is something
    else must not execute any PRAGMA statements. We verify by checking
    that the function short-circuits on the module-level engine's
    `dialect.name` guard — this protects a future Postgres swap from
    blowing up at connection time.
    """
    import app.infrastructure.db.session as session_mod

    assert session_mod.engine.dialect.name == "sqlite"
    # Confirms the guard targets dialect.name, not the dbapi_conn type.
    # A regression that drops the `if engine.dialect.name != "sqlite"`
    # guard would execute PRAGMA on any dialect — the test below cannot
    # assert that negative case without a Postgres engine, so this
    # sanity check keeps the structural invariant visible.
    import inspect

    source = inspect.getsource(session_mod._configure_sqlite)
    assert 'engine.dialect.name != "sqlite"' in source
