# ABOUTME: SourceKind-keyed extractor registry consumed by GenerateFromSource.
# ABOUTME: Missing-key lookup raises UnsupportedSourceKind at the app boundary.
"""Source-text extractor registry keyed by SourceKind."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.application.exceptions import UnsupportedSourceKind
from app.application.ports import SourceTextExtractor
from app.application.registry import Registry
from app.domain.value_objects import SourceKind


class SourceTextExtractorRegistry(Registry[SourceKind, SourceTextExtractor]):
    """Resolve a SourceKind to its registered text-extractor callable."""

    def __init__(
        self,
        extractors: Mapping[SourceKind, SourceTextExtractor] = (
            MappingProxyType({})
        ),
    ) -> None:
        """Register extractors keyed by source kind."""
        super().__init__(entries=extractors)

    def _missing_error(self, key: SourceKind) -> Exception:
        """Return UnsupportedSourceKind for an unregistered kind."""
        return UnsupportedSourceKind(
            f"Source kind {key.value!r} not supported yet"
        )
