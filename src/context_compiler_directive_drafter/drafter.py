"""Synchronous orchestration for non-authoritative directive drafting."""

from collections.abc import Callable
from dataclasses import dataclass

from context_compiler.grammar import CanonicalDirective

from context_compiler_directive_drafter.heuristic_preprocessor import (
    PreprocessResult,
    preprocess_heuristic,
)
from context_compiler_directive_drafter.output_validation import parse_preprocessor_output


@dataclass(frozen=True)
class UnknownDirective:
    """Represent an unresolved drafting result."""

    reason: str


@dataclass(frozen=True)
class NoDirective:
    """Represent a confident non-directive drafting result."""

    reason: str


DraftResultType = CanonicalDirective | UnknownDirective | NoDirective


@dataclass(frozen=True)
class DraftResult:
    """Structured non-authoritative result for one high-level drafting pass.

    The result exposes only the final drafting producer plus one validated
    drafting-layer result variant. It does not imply compiler approval,
    directive application, or authoritative state mutation.
    """

    source: str
    result: DraftResultType


DraftFallback = Callable[[str], DraftResult]


class DirectiveDrafter:
    """Synchronous high-level drafting API over the public helper functions.

    This class orchestrates heuristic preprocessing and validation without
    becoming an authority over compiler state. It proposes at most one
    canonical directive per call and leaves authoritative review and
    application to `context-compiler`.
    """

    def __init__(self, fallback: DraftFallback | None = None) -> None:
        """Create a drafter with an optional fallback acquisition callback.

        Args:
            fallback: Optional non-authoritative callback that accepts the
                original user input and returns a DraftResult. The callback is
                only used when heuristic drafting does not produce a canonical
                directive.
        """

        self._fallback = fallback

    def draft_directive(self, user_input: str) -> DraftResult:
        """Draft at most one canonical directive from one user input."""

        heuristic_result = preprocess_heuristic(user_input)
        drafted = _heuristic_result_to_draft_result(heuristic_result)

        if not isinstance(drafted.result, CanonicalDirective) and self._fallback is not None:
            drafted = self._fallback(user_input)

        return _validate_draft_result(drafted)


def _heuristic_result_to_draft_result(heuristic_result: PreprocessResult) -> DraftResult:
    if heuristic_result["outcome"] == "directive":
        directive = heuristic_result["directive"]
        canonical = parse_preprocessor_output(directive)
        if canonical is None:
            return DraftResult(
                source="heuristic",
                result=UnknownDirective(reason="invalid_canonical_directive"),
            )
        return DraftResult(source="heuristic", result=canonical)

    reason = heuristic_result["reason"]

    if heuristic_result["outcome"] == "unknown":
        return DraftResult(source="heuristic", result=UnknownDirective(reason=reason))

    return DraftResult(source="heuristic", result=NoDirective(reason=reason))


def _validate_draft_result(drafted: DraftResult) -> DraftResult:
    if not isinstance(drafted.result, CanonicalDirective):
        return drafted

    validated_directive = parse_preprocessor_output(drafted.result.text)
    if validated_directive is None:
        return DraftResult(
            source=drafted.source,
            result=UnknownDirective(reason="invalid_canonical_directive"),
        )

    return DraftResult(source=drafted.source, result=validated_directive)
