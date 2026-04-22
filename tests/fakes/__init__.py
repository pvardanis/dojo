# ABOUTME: Hand-written fakes for every application port.
# ABOUTME: No Mock(); tests import `from tests.fakes import Fake*`.
"""Hand-written fake adapters (one per port)."""

from tests.fakes.fake_card_repository import FakeCardRepository
from tests.fakes.fake_card_review_repository import (
    FakeCardReviewRepository,
)
from tests.fakes.fake_draft_store import FakeDraftStore
from tests.fakes.fake_llm_provider import FakeLLMProvider
from tests.fakes.fake_note_repository import FakeNoteRepository
from tests.fakes.fake_source_repository import FakeSourceRepository

__all__ = [
    "FakeCardRepository",
    "FakeCardReviewRepository",
    "FakeDraftStore",
    "FakeLLMProvider",
    "FakeNoteRepository",
    "FakeSourceRepository",
]
