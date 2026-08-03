"""Synchronous orchestration for non-authoritative directive drafting."""

from collections.abc import Callable
from dataclasses import dataclass

from context_compiler_directive_drafter.constants import DRAFT_OUTCOME_DIRECTIVE, DraftOutcome
from context_compiler_directive_drafter.heuristic_preprocessor import preprocess_heuristic
from context_compiler_directive_drafter.output_validation import parse_preprocessor_output


@dataclass(frozen=True)
class DraftResult:
    """Structured non-authoritative outcome for one high-level drafting pass.

    The result exposes only the host-visible drafting outcome plus any final
    directive proposal. It does not imply compiler approval, policy
    validation, or authoritative state mutation.
    """

    outcome: DraftOutcome
    directive: str | None


DraftFallback = Callable[[str], DraftResult]


class DirectiveDrafter:
    """Synchronous high-level drafting API over the public helper functions.

    This class orchestrates preprocessing and validation without becoming an
    authority over compiler state. It proposes at most one canonical directive
    per call and leaves authoritative review and application to
    `context-compiler`.
    """

    def __init__(self, fallback: DraftFallback | None = None) -> None:
        """Create a drafter with an optional fallback acquisition callback.

        Args:
            fallback: Optional non-authoritative callback that accepts the
                original user input and returns a DraftResult. The callback is
                only used when heuristic drafting does not produce a directive.
        """

        self._fallback = fallback

    def draft_directive(self, user_input: str) -> DraftResult:
        """Draft at most one canonical directive from one user input.

        Args:
            user_input: Raw user text to interpret as a possible directive.

        Returns:
            A DraftResult containing the explicit drafting outcome and the
            final directive proposal, if one was produced.
        """

        heuristic_result = preprocess_heuristic(user_input)
        drafted = DraftResult(
            outcome=heuristic_result["outcome"],
            directive=heuristic_result["directive"],
        )

        if drafted.outcome != DRAFT_OUTCOME_DIRECTIVE and self._fallback is not None:
            drafted = self._fallback(user_input)

        if drafted.outcome != DRAFT_OUTCOME_DIRECTIVE:
            return drafted

        validated_directive = parse_preprocessor_output(drafted.directive)
        if validated_directive is None:
            return DraftResult(outcome="unknown", directive=None)

        return DraftResult(outcome=drafted.outcome, directive=validated_directive)
