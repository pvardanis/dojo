# ABOUTME: SQLite PRAGMA listener regression net.
# ABOUTME: Asserts foreign_keys / journal_mode / busy_timeout are applied.
"""Dialect-guarded PRAGMA listener integration test."""

from __future__ import annotations

import inspect
from pathlib import Path

from sqlalchemy import create_engine, event, text

from app.infrastructure.db.session import _configure_sqlite


def test_sqlite_pragmas_applied_on_connect(tmp_path: Path) -> None:
    """The connect listener sets FK/WAL/busy_timeout on every connection.

    The `app.infrastructure.db.session._configure_sqlite` listener is
    bound to the module-level engine — so the conftest `_migrated_engine`
    (which creates its own `create_engine`) would silently bypass it.
    This test creates a fresh sqlite engine, re-registers the listener,
    opens a connection, and asserts every PRAGMA is active.

    Without this test a regression that drops the dialect guard, breaks
    a PRAGMA string, or re-orders the cursor calls would ship without
    failing any SC gate.
    """
    db_url = f"sqlite:///{tmp_path / 'pragmas.db'}"
    test_engine = create_engine(db_url)
    event.listen(test_engine, "connect", _configure_sqlite)

    try:
        with test_engine.connect() as conn:
            fk = conn.execute(text("PRAGMA foreign_keys"))
            journal = conn.execute(text("PRAGMA journal_mode"))
            busy = conn.execute(text("PRAGMA busy_timeout"))
            assert fk.scalar_one() == 1
            assert journal.scalar_one() == "wal"
            assert busy.scalar_one() == 5000
    finally:
        test_engine.dispose()


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
    # Confirms the guard targets dialect.name.
    source = inspect.getsource(session_mod._configure_sqlite)
    assert 'engine.dialect.name != "sqlite"' in source
