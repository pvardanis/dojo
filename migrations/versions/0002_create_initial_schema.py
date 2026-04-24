# ABOUTME: Alembic migration — create the four Phase 3 tables.
# ABOUTME: Stacks on the empty 0001 baseline (CONTEXT D-08a).

"""create initial schema

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-24 13:28:17.459857

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create sources, notes, cards, card_reviews tables.

    Order: parents first — ``sources`` before ``notes`` and ``cards``,
    ``cards`` before ``card_reviews`` — so the FK references resolve.
    """
    op.create_table(
        "sources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("user_prompt", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("identifier", sa.String(), nullable=True),
        sa.Column("source_text", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "kind IN ('file', 'url', 'topic')",
            name="ck_sources_kind",
        ),
    )
    op.create_table(
        "notes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content_md", sa.String(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("answer", sa.String(), nullable=False),
        sa.Column("tags", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "card_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("card_id", sa.String(), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["cards.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "rating IN ('correct', 'incorrect')",
            name="ck_card_reviews_rating",
        ),
    )


def downgrade() -> None:
    """Drop the four Phase 3 tables in reverse-create order."""
    op.drop_table("card_reviews")
    op.drop_table("cards")
    op.drop_table("notes")
    op.drop_table("sources")
