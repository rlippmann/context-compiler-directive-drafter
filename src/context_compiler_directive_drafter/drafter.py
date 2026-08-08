"""High-level orchestration for non-authoritative directive drafting."""

from collections.abc import Awaitable, Callable
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

    The result exposes only the final drafting producer plus one parsed
    drafting-layer result variant. It does not imply compiler approval,
    directive application, or authoritative state mutation.
    """

    source: str
    result: DraftResultType


DraftFallback = Callable[[str], DraftResult]
AsyncDraftFallback = Callable[[str], Awaitable[DraftResult]]


class DirectiveDrafter:
    """High-level drafting API over the public helper functions.

    This class orchestrates heuristic preprocessing, optional sync or async
    fallback acquisition, and result validation without becoming an authority
    over compiler state. It proposes at most one canonical directive per call
    and leaves authoritative review and application to `context-compiler`.
    """

    def __init__(
        self,
        fallback: DraftFallback | None = None,
        async_fallback: AsyncDraftFallback | None = None,
    ) -> None:
        """Create a drafter with optional fallback acquisition callbacks.

        Args:
            fallback: Optional non-authoritative callback that accepts the
                original user input and returns a DraftResult. The callback is
                only used when heuristic drafting does not produce a directly
                returnable result.
            async_fallback: Optional non-authoritative async callback that
                accepts the original user input and returns a DraftResult. The
                callback is only used by async drafting when heuristic drafting
                does not produce a directly returnable result.
        """

        self._fallback = fallback
        self._async_fallback = async_fallback

    @property
    def fallback(self) -> DraftFallback | None:
        """Return the configured fallback acquisition callback, if any."""

        return self._fallback

    @fallback.setter
    def fallback(self, fallback: DraftFallback | None) -> None:
        """Set or clear the fallback acquisition callback."""

        self._fallback = fallback

    @property
    def async_fallback(self) -> AsyncDraftFallback | None:
        """Return the configured async fallback acquisition callback, if any."""

        return self._async_fallback

    @async_fallback.setter
    def async_fallback(self, async_fallback: AsyncDraftFallback | None) -> None:
        """Set or clear the async fallback acquisition callback."""

        self._async_fallback = async_fallback

    def draft_directive(self, user_input: str) -> DraftResult:
        """Draft at most one canonical directive from one user input.

        The drafter always attempts heuristic preprocessing first. When that
        heuristic result is not fallback-eligible, it is returned immediately.
        When it is, the drafter may invoke the optional fallback acquisition
        callback and returns that callback's DraftResult instead.
        """

        heuristic_result = preprocess_heuristic(user_input)
        heuristic_draft = _heuristic_result_to_draft_result(heuristic_result)

        if not _is_fallback_eligible(heuristic_draft) or self._fallback is None:
            return _normalize_draft_result(heuristic_draft)

        fallback_draft = self._fallback(user_input)
        return _normalize_draft_result(fallback_draft)

    async def async_draft_directive(self, user_input: str) -> DraftResult:
        """Draft at most one canonical directive from one user input asynchronously.

        The drafter always attempts heuristic preprocessing first. When that
        heuristic result is not fallback-eligible, it is returned immediately.
        When it is, the drafter may await the optional async fallback
        acquisition callback and returns that callback's DraftResult instead.
        """

        heuristic_result = preprocess_heuristic(user_input)
        heuristic_draft = _heuristic_result_to_draft_result(heuristic_result)

        if not _is_fallback_eligible(heuristic_draft) or self._async_fallback is None:
            return _normalize_draft_result(heuristic_draft)

        fallback_draft = await self._async_fallback(user_input)
        return _normalize_draft_result(fallback_draft)


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


def _is_fallback_eligible(drafted: DraftResult) -> bool:
    if isinstance(drafted.result, CanonicalDirective):
        return False
    return isinstance(drafted.result, NoDirective | UnknownDirective)


def _normalize_draft_result(drafted: DraftResult) -> DraftResult:
    if not isinstance(drafted.result, CanonicalDirective):
        return drafted

    decomposed_directive = parse_preprocessor_output(drafted.result.text)
    if decomposed_directive is None:
        return DraftResult(
            source=drafted.source,
            result=UnknownDirective(reason="invalid_canonical_directive"),
        )

    return DraftResult(source=drafted.source, result=decomposed_directive)
