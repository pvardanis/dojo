# ABOUTME: List-backed fake CardReviewRepository — append-only log.
# ABOUTME: Tests assert on the list order of `.saved`.
"""FakeCardReviewRepository — hand-written list-backed fake."""

from __future__ import annotations

from app.domain.entities import CardReview


class FakeCardReviewRepository:
    """Append-only list of CardReview entries."""

    def __init__(self) -> None:
        """Start with empty review log."""
        self.saved: list[CardReview] = []

    def save(self, review: CardReview) -> None:
        """Append the review to the log."""
        self.saved.append(review)
