"""High-level orchestration for non-authoritative directive drafting."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from context_compiler.grammar import CanonicalDirective, decompose_directive

from context_compiler_directive_drafter.constants import (
    _PREPROCESSOR_NO_DIRECTIVE_SENTINEL,
    _REASON_COMPOUND_DIRECTIVE,
    _REASON_INCOMPLETE_DIRECTIVE,
    _REASON_MALFORMED_DIRECTIVE,
    _REASON_MULTI_SENTENCE,
    _REASON_ORDINARY_NON_DIRECTIVE,
    _REASON_QUESTION_FORM,
    _REASON_QUOTED_REPORTED,
    _REASON_UNSUPPORTED_INPUT,
    REASON_INCOMPLETE,
    REASON_INVALID_CANDIDATE,
    REASON_MULTIPLE_DIRECTIVES,
    REASON_NON_DIRECTIVE,
    RejectedReason,
    UnknownReason,
)
from context_compiler_directive_drafter.heuristic_preprocessor import (
    _preprocess_heuristic,
    _PreprocessResult,
)


@dataclass(frozen=True)
class UnknownDirective:
    """Represent semantic uncertainty that may be sent to fallback."""

    reason: UnknownReason


@dataclass(frozen=True)
class RejectedDirective:
    """Represent a terminal acquisition rejection."""

    reason: RejectedReason


_DraftResultType = CanonicalDirective | RejectedDirective | UnknownDirective


@dataclass(frozen=True)
class DraftResult:
    """Structured non-authoritative result for one high-level drafting pass.

    The result exposes only the final drafting producer plus one parsed
    drafting-layer result variant. It does not imply compiler approval,
    directive application, or authoritative state mutation.
    """

    source: str
    result: _DraftResultType


_DraftFallback = Callable[[str], str | None]
_AsyncDraftFallback = Callable[[str], Awaitable[str | None]]


class DirectiveDrafter:
    """High-level drafting API over the public helper functions.

    This class orchestrates heuristic preprocessing, optional sync or async
    fallback acquisition, and result validation without becoming an authority
    over compiler state. It proposes at most one canonical directive per call
    and leaves authoritative review and application to `context-compiler`.
    """

    def __init__(
        self,
        fallback: _DraftFallback | None = None,
        fallback_source: str = "fallback",
        async_fallback: _AsyncDraftFallback | None = None,
        async_fallback_source: str = "fallback",
    ) -> None:
        """Create a drafter with optional fallback acquisition callbacks.

        Args:
            fallback: Optional non-authoritative callback that accepts the
                original user input and returns candidate directive text or
                None. The callback is only used when heuristic drafting does
                not produce a directly returnable result.
            fallback_source: Source metadata to preserve on DraftResult values
                produced from the configured sync fallback callback.
            async_fallback: Optional non-authoritative async callback that
                accepts the original user input and returns candidate
                directive text or None. The callback is only used by async
                drafting when heuristic drafting does not produce a directly
                returnable result.
            async_fallback_source: Source metadata to preserve on DraftResult
                values produced from the configured async fallback callback.
        """

        self._fallback: _DraftFallback | None = None
        self._fallback_source = fallback_source
        self._async_fallback: _AsyncDraftFallback | None = None
        self._async_fallback_source = async_fallback_source

        if fallback is not None:
            self.configure_fallback(fallback, source=fallback_source)
        if async_fallback is not None:
            self.configure_async_fallback(async_fallback, source=async_fallback_source)

    @property
    def fallback(self) -> bool:
        """Return whether a sync fallback acquisition callback is configured."""

        return self._fallback is not None

    @property
    def async_fallback(self) -> bool:
        """Return whether an async fallback acquisition callback is configured."""

        return self._async_fallback is not None

    def configure_fallback(self, fallback: _DraftFallback, *, source: str) -> None:
        """Configure a sync fallback acquisition callback and its source metadata."""

        self._fallback = fallback
        self._fallback_source = source

    def clear_fallback(self) -> None:
        """Clear the configured sync fallback acquisition callback."""

        self._fallback = None

    def configure_async_fallback(self, async_fallback: _AsyncDraftFallback, *, source: str) -> None:
        """Configure an async fallback acquisition callback and its source metadata."""

        self._async_fallback = async_fallback
        self._async_fallback_source = source

    def clear_async_fallback(self) -> None:
        """Clear the configured async fallback acquisition callback."""

        self._async_fallback = None

    def draft_directive(self, user_input: str) -> DraftResult:
        """Draft at most one canonical directive from one user input.

        The drafter always attempts heuristic preprocessing first. When that
        heuristic result is not fallback-eligible, it is returned immediately.
        When it is, the drafter may invoke the optional fallback acquisition
        callback, parse and validate its returned candidate text, and build
        the final DraftResult itself.
        """

        heuristic_result = _preprocess_heuristic(user_input)
        heuristic_draft = _heuristic_result_to_draft_result(heuristic_result)

        if not _is_fallback_eligible(heuristic_draft) or self._fallback is None:
            return heuristic_draft

        fallback_text = self._fallback(user_input)
        return _draft_result_from_fallback_output(fallback_text, source=self._fallback_source)

    async def async_draft_directive(self, user_input: str) -> DraftResult:
        """Draft at most one canonical directive from one user input asynchronously.

        The drafter always attempts heuristic preprocessing first. When that
        heuristic result is not fallback-eligible, it is returned immediately.
        When it is, the drafter may await the optional async fallback
        acquisition callback, parse and validate its returned candidate text,
        and build the final DraftResult itself.
        """

        heuristic_result = _preprocess_heuristic(user_input)
        heuristic_draft = _heuristic_result_to_draft_result(heuristic_result)

        if not _is_fallback_eligible(heuristic_draft) or self._async_fallback is None:
            return heuristic_draft

        fallback_text = await self._async_fallback(user_input)
        return _draft_result_from_fallback_output(fallback_text, source=self._async_fallback_source)


def _heuristic_result_to_draft_result(heuristic_result: _PreprocessResult) -> DraftResult:
    if heuristic_result["outcome"] == "directive":
        directive = heuristic_result["directive"]
        return DraftResult(source="heuristic", result=directive)

    reason = heuristic_result["reason"]

    if heuristic_result["outcome"] == "unknown":
        return DraftResult(
            source="heuristic",
            result=UnknownDirective(reason=cast(UnknownReason, reason)),
        )

    return DraftResult(
        source="heuristic",
        result=RejectedDirective(reason=_public_rejection_reason(reason)),
    )


def _public_rejection_reason(reason: str) -> RejectedReason:
    if reason in {
        _REASON_ORDINARY_NON_DIRECTIVE,
        _REASON_QUESTION_FORM,
        _REASON_QUOTED_REPORTED,
        _REASON_MALFORMED_DIRECTIVE,
    }:
        return REASON_NON_DIRECTIVE
    if reason == _REASON_INCOMPLETE_DIRECTIVE:
        return REASON_INCOMPLETE
    if reason in {_REASON_COMPOUND_DIRECTIVE, _REASON_UNSUPPORTED_INPUT}:
        return REASON_MULTIPLE_DIRECTIVES
    if reason == _REASON_MULTI_SENTENCE:
        return REASON_NON_DIRECTIVE
    raise ValueError(f"Unsupported terminal heuristic reason: {reason!r}")


def _is_fallback_eligible(drafted: DraftResult) -> bool:
    return isinstance(drafted.result, UnknownDirective)


def _draft_result_from_fallback_output(fallback_text: str | None, *, source: str) -> DraftResult:
    if fallback_text is None:
        return DraftResult(
            source=source,
            result=RejectedDirective(reason=REASON_NON_DIRECTIVE),
        )

    if fallback_text.strip().upper() == _PREPROCESSOR_NO_DIRECTIVE_SENTINEL:
        return DraftResult(
            source=source,
            result=RejectedDirective(reason=REASON_NON_DIRECTIVE),
        )

    parsed = decompose_directive(fallback_text.strip())
    if isinstance(parsed, CanonicalDirective):
        return DraftResult(source=source, result=parsed)

    return DraftResult(
        source=source,
        result=RejectedDirective(reason=REASON_INVALID_CANDIDATE),
    )
