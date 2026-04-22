# ABOUTME: Domain-layer exception hierarchy rooted at DojoError.
# ABOUTME: Application + infrastructure exceptions inherit from DojoError.
"""Domain-layer exceptions."""

from __future__ import annotations


class DojoError(Exception):
    """Base class for all Dojo domain and application exceptions."""
