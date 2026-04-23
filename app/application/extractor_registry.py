# ABOUTME: SourceKind-keyed extractor registry consumed by GenerateFromSource.
# ABOUTME: Missing-key lookup raises UnsupportedSourceKind at the app boundary.
"""Source-text extractor registry keyed by SourceKind."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.application.exceptions import (
    ExtractorNotApplicable,
    UnsupportedSourceKind,
)
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
        """Register extractors keyed by source kind.

        :param extractors: Mapping of `SourceKind` to its extractor
            callable. Defaults empty; in Phase 2 the registry is wired
            empty and only FILE/URL lookups raise. Phase 4's composition
            root supplies the real FILE/URL extractors here.
        """
        super().__init__(entries=extractors)

    def _missing_error(self, key: SourceKind) -> Exception:
        """Map a missing kind to its domain-appropriate error.

        `TOPIC` has no extractor by design (source text is `None`);
        asking the registry for it is a category mismatch and raises
        `ExtractorNotApplicable`. Every other unregistered kind is a
        "not wired yet" state and raises `UnsupportedSourceKind`.

        :param key: The unregistered `SourceKind` that was looked up.
        :returns: `ExtractorNotApplicable` when `key` is `TOPIC`;
            otherwise `UnsupportedSourceKind` naming the kind value.
        """
        if key is SourceKind.TOPIC:
            return ExtractorNotApplicable(
                "TOPIC has no extractor — source_text is None by design;"
                " callers must bypass the registry for TOPIC"
            )
        return UnsupportedSourceKind(
            f"Source kind {key.value!r} not supported yet"
        )
