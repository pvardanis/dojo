# ABOUTME: Async SQLAlchemy engine + session factory.
# ABOUTME: Dialect-guarded connection listener sets SQLite pragmas.
"""Async SQLAlchemy engine + session factory for Dojo."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models (populated in Phase 3)."""


_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,  # C3 mitigation
    class_=AsyncSession,
)


@event.listens_for(engine.sync_engine, "connect")
def _configure_sqlite(dbapi_conn, _):
    """Apply SQLite-only pragmas; no-op on other dialects."""
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
