# ABOUTME: Smoke test — Base.metadata sees the four Phase 3 tables.
# ABOUTME: Catches PITFALL M9 "env.py imports Base but not models.py".
"""Alembic metadata smoke test (RESEARCH R5)."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKeyConstraint

from app.infrastructure.db import models as _models  # noqa: F401
from app.infrastructure.db.session import Base


def test_base_metadata_has_four_phase_3_tables() -> None:
    """Importing models registers sources/notes/cards/card_reviews."""
    assert set(Base.metadata.tables) == {
        "sources",
        "notes",
        "cards",
        "card_reviews",
    }


def test_notes_and_cards_have_fk_to_sources() -> None:
    """`notes.source_id` and `cards.source_id` reference `sources.id`.

    Confirms the declarative `ForeignKey` in `models.py` makes it into
    `Base.metadata` (and therefore into the autogenerate diff path).
    """
    for child_table_name in ("notes", "cards"):
        table = Base.metadata.tables[child_table_name]
        fk_constraints = [
            c for c in table.constraints if isinstance(c, ForeignKeyConstraint)
        ]
        assert len(fk_constraints) == 1, (
            f"expected one FK on {child_table_name}, "
            f"found {len(fk_constraints)}"
        )
        fk = fk_constraints[0]
        assert [c.name for c in fk.columns] == ["source_id"]
        referred_col = next(iter(fk.elements)).target_fullname
        assert referred_col == "sources.id"


def test_card_reviews_fk_cascades_from_cards() -> None:
    """`card_reviews.card_id` references `cards.id` with CASCADE delete."""
    table = Base.metadata.tables["card_reviews"]
    fk_constraints = [
        c for c in table.constraints if isinstance(c, ForeignKeyConstraint)
    ]
    assert len(fk_constraints) == 1
    fk = fk_constraints[0]
    assert [c.name for c in fk.columns] == ["card_id"]
    assert next(iter(fk.elements)).target_fullname == "cards.id"
    assert fk.ondelete == "CASCADE"


def test_sources_has_kind_check_constraint() -> None:
    """`sources.kind` is constrained to the three SourceKind values."""
    table = Base.metadata.tables["sources"]
    checks = [c for c in table.constraints if isinstance(c, CheckConstraint)]
    assert any(c.name == "ck_sources_kind" for c in checks)


def test_card_reviews_has_rating_check_constraint() -> None:
    """`card_reviews.rating` is constrained to the two Rating values."""
    table = Base.metadata.tables["card_reviews"]
    checks = [c for c in table.constraints if isinstance(c, CheckConstraint)]
    assert any(c.name == "ck_card_reviews_rating" for c in checks)
