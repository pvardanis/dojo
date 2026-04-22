# ABOUTME: Application-layer exception hierarchy.
# ABOUTME: Every class inherits from app.domain.exceptions.DojoError.
"""Application-layer exceptions."""

from __future__ import annotations

from app.domain.exceptions import DojoError


class UnsupportedSourceKind(DojoError):
    """Raised when a source kind is not yet supported by the use case."""


class DraftExpired(DojoError):
    """Raised when a draft token has expired or was already popped."""


class LLMOutputMalformed(DojoError):
    """Raised when the LLM's structured output fails DTO validation."""
