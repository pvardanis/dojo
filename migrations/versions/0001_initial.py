# ABOUTME: Initial empty Alembic revision.
# ABOUTME: Creates the alembic_version tracking table as a side effect.

"""initial

Revision ID: 0001
Revises:
Create Date: 2026-04-20 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No schema changes in Phase 1; Phase 3 adds real tables."""


def downgrade() -> None:
    """No-op; initial revision has nothing to undo."""
