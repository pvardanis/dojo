# ABOUTME: Unit tests — mapper round-trip, no DB, pure functions.
# ABOUTME: Catches UUID↔str, enum↔str, tags JSON drift.
"""Pure-function mapper round-trip tests (PERSIST-02)."""

from __future__ import annotations

import uuid

import pytest

from app.application.exceptions import RepositoryRowCorrupt
from app.domain.entities import Card, CardReview, Note, Source
from app.domain.value_objects import (
    CardId,
    Rating,
    SourceId,
    SourceKind,
)
from app.infrastructure.db.mappers import (
    card_from_row,
    card_review_from_row,
    card_review_to_row,
    card_to_row,
    note_from_row,
    note_to_row,
    source_from_row,
    source_to_row,
)
from app.infrastructure.db.models import CardRow, SourceRow


def test_source_round_trip() -> None:
    """Source → row → Source preserves every field."""
    src = Source(
        kind=SourceKind.TOPIC,
        user_prompt="p",
        display_name="d",
    )
    assert source_from_row(source_to_row(src)) == src


def test_source_file_kind_round_trips() -> None:
    """FILE kind survives .value↔Enum conversion."""
    src = Source(
        kind=SourceKind.FILE,
        user_prompt="p",
        display_name="d",
        identifier="/tmp/x.md",
        source_text="hello",
    )
    assert source_from_row(source_to_row(src)) == src


def test_note_round_trip() -> None:
    """Note → row → Note preserves source_id UUID and generated_at."""
    note = Note(
        source_id=SourceId(uuid.uuid4()),
        title="t",
        content_md="c",
    )
    assert note_from_row(note_to_row(note)) == note


def test_card_round_trip_with_tags() -> None:
    """Card tags tuple survives JSON round-trip."""
    card = Card(
        source_id=SourceId(uuid.uuid4()),
        question="q",
        answer="a",
        tags=("python", "sql"),
    )
    assert card_from_row(card_to_row(card)) == card


def test_card_round_trip_empty_tags() -> None:
    """Empty tags tuple stored as '[]' reads back as ()."""
    card = Card(
        source_id=SourceId(uuid.uuid4()),
        question="q",
        answer="a",
    )
    roundtripped = card_from_row(card_to_row(card))
    assert roundtripped.tags == ()
    assert roundtripped == card


def test_card_review_round_trip_correct() -> None:
    """CardReview rating survives Rating.value↔Rating (correct)."""
    review = CardReview(
        card_id=CardId(uuid.uuid4()),
        rating=Rating.CORRECT,
    )
    roundtripped = card_review_from_row(card_review_to_row(review))
    assert roundtripped == review
    assert roundtripped.is_correct is True


def test_card_review_round_trip_incorrect() -> None:
    """Rating.INCORRECT also survives the mapper round-trip."""
    review = CardReview(
        card_id=CardId(uuid.uuid4()),
        rating=Rating.INCORRECT,
    )
    roundtripped = card_review_from_row(card_review_to_row(review))
    assert roundtripped == review
    assert roundtripped.is_correct is False


def test_source_url_kind_round_trips() -> None:
    """URL kind survives .value↔Enum conversion."""
    src = Source(
        kind=SourceKind.URL,
        user_prompt="p",
        display_name="d",
        identifier="https://example.com/article",
        source_text="extracted body",
    )
    assert source_from_row(source_to_row(src)) == src


def test_source_created_at_is_timezone_aware_after_round_trip() -> None:
    """A tz-aware `created_at` survives persist→load without becoming naive.

    Domain entities set `created_at = datetime.now(UTC)` (aware). The
    existing round-trip tests compare `src == src` after round-trip,
    which would pass even if tzinfo were silently stripped because
    two references to the same default-factory result are `==` by
    definition. This test constructs an explicit aware timestamp and
    asserts both that the values compare equal AND that the retrieved
    tzinfo is non-None.
    """
    from datetime import UTC, datetime

    fixed = datetime(2026, 4, 24, 12, 34, 56, tzinfo=UTC)
    src = Source(
        kind=SourceKind.TOPIC,
        user_prompt="p",
        display_name="d",
        created_at=fixed,
    )
    roundtripped = source_from_row(source_to_row(src))
    assert roundtripped.created_at == fixed
    assert roundtripped.created_at.tzinfo is not None


# --- Corruption paths ----------------------------------------------------
#
# Every `*_from_row` funnels stdlib parse failures through
# `_parse_or_corrupt`, which raises `RepositoryRowCorrupt`. The tests
# below confirm that each parse site (UUID, enum, JSON tags) translates
# rather than leaking `ValueError` / `JSONDecodeError`.


def _make_source_row(**overrides: object) -> SourceRow:
    """Build a well-formed SourceRow and apply targeted overrides."""
    from datetime import UTC, datetime

    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "kind": SourceKind.TOPIC.value,
        "user_prompt": "p",
        "display_name": "d",
        "identifier": None,
        "source_text": None,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return SourceRow(**defaults)  # type: ignore[arg-type]


def _make_card_row(**overrides: object) -> CardRow:
    """Build a well-formed CardRow and apply targeted overrides."""
    from datetime import UTC, datetime

    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "source_id": str(uuid.uuid4()),
        "question": "q",
        "answer": "a",
        "tags": "[]",
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return CardRow(**defaults)  # type: ignore[arg-type]


def test_source_from_row_raises_on_bad_uuid() -> None:
    """Corrupted id column surfaces as RepositoryRowCorrupt, not ValueError."""
    row = _make_source_row(id="not-a-uuid")
    with pytest.raises(RepositoryRowCorrupt) as exc_info:
        source_from_row(row)
    assert exc_info.value.table == "sources"
    assert exc_info.value.field == "id"
    assert "not-a-uuid" in exc_info.value.value


def test_source_from_row_raises_on_bad_kind() -> None:
    """Unknown enum string raises RepositoryRowCorrupt on the kind field."""
    row = _make_source_row(kind="NOT_A_KIND")
    with pytest.raises(RepositoryRowCorrupt) as exc_info:
        source_from_row(row)
    assert exc_info.value.field == "kind"
    assert exc_info.value.value == "NOT_A_KIND"


def test_card_from_row_raises_on_bad_json_tags() -> None:
    """Malformed JSON in tags column raises RepositoryRowCorrupt."""
    row = _make_card_row(tags="not json")
    with pytest.raises(RepositoryRowCorrupt) as exc_info:
        card_from_row(row)
    assert exc_info.value.field == "tags"


def test_card_from_row_raises_when_tags_json_is_not_a_list() -> None:
    """Valid JSON of the wrong shape also raises RepositoryRowCorrupt."""
    row = _make_card_row(tags='{"a": 1}')
    with pytest.raises(RepositoryRowCorrupt) as exc_info:
        card_from_row(row)
    assert exc_info.value.field == "tags"


def test_repository_row_corrupt_chains_original_cause() -> None:
    """Chained __cause__ preserves the stdlib root cause for debugging."""
    row = _make_source_row(id="not-a-uuid")
    with pytest.raises(RepositoryRowCorrupt) as exc_info:
        source_from_row(row)
    assert isinstance(exc_info.value.__cause__, ValueError)
