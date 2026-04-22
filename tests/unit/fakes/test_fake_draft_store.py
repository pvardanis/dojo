# ABOUTME: FakeDraftStore contract tests — put/pop atomicity, expiry.
# ABOUTME: Proves the fake's state is exposed via .puts public attribute.
"""FakeDraftStore unit tests."""

from __future__ import annotations

import uuid

from app.application.dtos import CardDTO, DraftBundle, NoteDTO
from app.application.ports import DraftToken
from tests.fakes.fake_draft_store import FakeDraftStore


def _sample_bundle() -> DraftBundle:
    """Build a minimal DraftBundle for tests."""
    return DraftBundle(
        note=NoteDTO(title="t", content_md="body"),
        cards=[CardDTO(question="q?", answer="a.")],
    )


def test_put_then_pop_returns_bundle() -> None:
    """put stores the bundle; pop returns it exactly once."""
    store = FakeDraftStore()
    token = DraftToken(uuid.uuid4())
    bundle = _sample_bundle()
    store.put(token, bundle)
    assert store.pop(token) == bundle


def test_pop_is_atomic_read_and_delete() -> None:
    """After a successful pop, a second pop returns None."""
    store = FakeDraftStore()
    token = DraftToken(uuid.uuid4())
    store.put(token, _sample_bundle())
    _first = store.pop(token)
    assert store.pop(token) is None


def test_pop_missing_returns_none() -> None:
    """pop on an unknown token returns None."""
    store = FakeDraftStore()
    assert store.pop(DraftToken(uuid.uuid4())) is None


def test_puts_log_records_every_write() -> None:
    """Every put is appended to .puts in insertion order."""
    store = FakeDraftStore()
    token_a = DraftToken(uuid.uuid4())
    token_b = DraftToken(uuid.uuid4())
    bundle_a = _sample_bundle()
    bundle_b = _sample_bundle()
    store.put(token_a, bundle_a)
    store.put(token_b, bundle_b)
    assert store.puts == [(token_a, bundle_a), (token_b, bundle_b)]


def test_force_expire_removes_token() -> None:
    """force_expire drops the token as if the TTL had fired."""
    store = FakeDraftStore()
    token = DraftToken(uuid.uuid4())
    store.put(token, _sample_bundle())
    store.force_expire(token)
    assert store.pop(token) is None
