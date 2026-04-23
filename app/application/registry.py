# ABOUTME: Generic key→value registry with a domain-specific missing-key error.
# ABOUTME: Subclasses implement `_missing_error` to surface a domain exception.
"""Generic registry with a domain-specific missing-key error."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Hashable, Mapping
from types import MappingProxyType


class Registry[K: Hashable, V](ABC):
    """Key-to-value registry with a domain-specific missing-key error."""

    def __init__(
        self,
        entries: Mapping[K, V] = MappingProxyType({}),
    ) -> None:
        """Initialize with a (possibly empty) entries mapping."""
        self._entries = entries

    def get(self, key: K) -> V:
        """Return the value for key; raise domain error if absent."""
        value = self._entries.get(key)
        if value is None:
            raise self._missing_error(key)
        return value

    @abstractmethod
    def _missing_error(self, key: K) -> Exception:
        """Return the domain-specific exception for a missing key."""
