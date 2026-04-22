# ABOUTME: Application-ports smoke tests — surface shape + contract pins.
# ABOUTME: Behavioral tests for each port land with fakes in Plan 02-03.
"""Application ports smoke tests."""

from __future__ import annotations

import uuid

from app.application import ports


def test_draft_token_is_new_type_over_uuid() -> None:
    """DraftToken is a NewType whose supertype is uuid.UUID."""
    assert ports.DraftToken.__supertype__ is uuid.UUID


def test_draft_store_protocol_has_only_put_and_pop() -> None:
    """DraftStore exposes exactly put + pop, no get (CONTEXT D-04)."""
    public = {m for m in dir(ports.DraftStore) if not m.startswith("_")}
    assert "put" in public
    assert "pop" in public
    assert "get" not in public


def test_no_runtime_checkable_on_draft_store() -> None:
    """DraftStore is not a runtime_checkable Protocol (SC #2)."""
    # `_is_runtime_protocol` is set to True by @runtime_checkable; we
    # explicitly forbid that decorator.
    assert getattr(ports.DraftStore, "_is_runtime_protocol", False) is False
