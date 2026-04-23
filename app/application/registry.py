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
        """Initialize with a (possibly empty) entries mapping.

        :param entries: Read-only ``Mapping`` of keys to values. Defaults
            to an empty ``MappingProxyType``; the registry never mutates
            it after construction.
        """
        self._entries = entries

    def get(self, key: K) -> V:
        """Return the value for key; raise a domain error if absent.

        :param key: The lookup key.
        :returns: The value registered for ``key``.
        :raises Exception: Whatever ``_missing_error(key)`` returns when
            the key is not in the entries mapping.
        """
        value = self._entries.get(key)
        if value is None:
            raise self._missing_error(key)
        return value

    @abstractmethod
    def _missing_error(self, key: K) -> Exception:
        """Return the domain-specific exception for a missing key.

        :param key: The key that was looked up but not found.
        :returns: The exception instance to raise — subclasses pick the
            type and message appropriate to their domain.
        """
