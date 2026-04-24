# ABOUTME: SQLAlchemy 2.0 ORM row classes — one per domain entity.
# ABOUTME: Mapped[...] annotations; no relationship() (CONTEXT D-02b).
"""ORM row classes (CONTEXT D-02d column types locked)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import Base


class SourceRow(Base):
    """Row class for the `sources` table."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(primary_key=True)
    kind: Mapped[str]
    user_prompt: Mapped[str]
    display_name: Mapped[str]
    identifier: Mapped[str | None]
    source_text: Mapped[str | None]
    created_at: Mapped[datetime]


class NoteRow(Base):
    """Row class for the `notes` table (regenerate-overwrites)."""

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(primary_key=True)
    source_id: Mapped[str]
    title: Mapped[str]
    content_md: Mapped[str]
    generated_at: Mapped[datetime]


class CardRow(Base):
    """Row class for the `cards` table (regenerate-appends)."""

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(primary_key=True)
    source_id: Mapped[str]
    question: Mapped[str]
    answer: Mapped[str]
    tags: Mapped[str]
    created_at: Mapped[datetime]


class CardReviewRow(Base):
    """Row class for the append-only `card_reviews` table."""

    __tablename__ = "card_reviews"

    id: Mapped[str] = mapped_column(primary_key=True)
    card_id: Mapped[str]
    rating: Mapped[str]
    reviewed_at: Mapped[datetime]
