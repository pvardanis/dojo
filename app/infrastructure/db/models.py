# ABOUTME: SQLAlchemy 2.0 ORM row classes — one per domain entity.
# ABOUTME: Mapped[...] annotations; no relationship() per CONTEXT D-02b.
"""ORM row classes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import Base


class SourceRow(Base):
    """Row class for the `sources` table."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('file', 'url', 'topic')",
            name="ck_sources_kind",
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    kind: Mapped[str]
    user_prompt: Mapped[str]
    display_name: Mapped[str]
    identifier: Mapped[str | None]
    source_text: Mapped[str | None]
    created_at: Mapped[datetime]


class NoteRow(Base):
    """Row class for the `notes` table."""

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE")
    )
    title: Mapped[str]
    content_md: Mapped[str]
    generated_at: Mapped[datetime]


class CardRow(Base):
    """Row class for the `cards` table."""

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE")
    )
    question: Mapped[str]
    answer: Mapped[str]
    # JSON-encoded tuple[str]; SQLite has no native array type, so
    # the mapper layer handles encode/decode at the persistence boundary.
    tags: Mapped[str]
    created_at: Mapped[datetime]


class CardReviewRow(Base):
    """Row class for the append-only `card_reviews` table."""

    __tablename__ = "card_reviews"
    __table_args__ = (
        CheckConstraint(
            "rating IN ('correct', 'incorrect')",
            name="ck_card_reviews_rating",
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    card_id: Mapped[str] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE")
    )
    rating: Mapped[str]
    reviewed_at: Mapped[datetime]
