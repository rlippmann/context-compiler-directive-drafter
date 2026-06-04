"""Minimal drafting placeholder API.

This package intentionally stops short of authoritative behavior.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DraftResult:
    """Non-authoritative draft output from natural-language input."""

    user_input: str
    candidate_directive: str | None
    confidence: float
    authoritative: bool = False
    rationale: str = "Drafting is not implemented yet."


def draft_directive(user_input: str) -> DraftResult:
    """Return a conservative placeholder result for future drafting logic."""

    return DraftResult(
        user_input=user_input,
        candidate_directive=None,
        confidence=0.0,
    )
