# ABOUTME: SQLAlchemy 2.0 ORM row classes — one per domain entity.
# ABOUTME: Mapped[...] annotations; no relationship() per CONTEXT D-02b.
"""ORM row classes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.value_objects import Rating, SourceKind
from app.infrastructure.db.session import Base

# Derive CHECK-constraint SQL from the domain enums so that adding a
# `SourceKind` / `Rating` variant propagates here automatically.
# The Alembic migration file keeps its hardcoded string — migrations
# are frozen schema snapshots and must stay reproducible regardless
# of what the current enum looks like.
_SOURCE_KIND_SQL = ", ".join(f"'{k.value}'" for k in SourceKind)
_RATING_SQL = ", ".join(f"'{r.value}'" for r in Rating)


class SourceRow(Base):
    """Row class for the `sources` table."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            f"kind IN ({_SOURCE_KIND_SQL})",
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
            f"rating IN ({_RATING_SQL})",
            name="ck_card_reviews_rating",
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    card_id: Mapped[str] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE")
    )
    rating: Mapped[str]
    reviewed_at: Mapped[datetime]
