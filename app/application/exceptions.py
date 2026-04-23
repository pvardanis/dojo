# ABOUTME: Application-layer exception hierarchy.
# ABOUTME: Every class inherits from app.domain.exceptions.DojoError.
"""Application-layer exceptions."""

from __future__ import annotations

from app.domain.exceptions import DojoError


class UnsupportedSourceKind(DojoError):
    """Raised when a source kind is not yet supported by the use case."""


class ExtractorNotApplicable(DojoError):
    """Raised when a SourceKind categorically has no extractor.

    Distinct from ``UnsupportedSourceKind``: this signals a category
    mismatch (e.g. TOPIC, whose source text is ``None`` by design and
    must bypass the registry), not a "not wired up yet" state.
    """


class DraftExpired(DojoError):
    """Raised when a draft token has expired or was already popped."""


class LLMOutputMalformed(DojoError):
    """Raised when the LLM's structured output fails DTO validation."""
