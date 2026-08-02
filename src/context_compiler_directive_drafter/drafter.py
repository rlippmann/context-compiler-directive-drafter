"""Synchronous orchestration for non-authoritative directive drafting."""

from dataclasses import dataclass

from context_compiler import Engine
from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter.constants import DraftOutcome
from context_compiler_directive_drafter.heuristic_preprocessor import preprocess_heuristic
from context_compiler_directive_drafter.refiner import refine_directive


@dataclass(frozen=True)
class DraftResult:
    """Structured non-authoritative outcome for one high-level drafting pass.

    The result exposes only the host-visible drafting outcome plus any final
    directive proposal. It does not imply compiler approval, policy
    validation, or authoritative state mutation.
    """

    outcome: DraftOutcome
    directive: str | None


class DirectiveDrafter:
    """Synchronous high-level drafting API over the public helper functions.

    This class orchestrates preprocessing and deterministic refinement without
    becoming an authority over compiler state. It proposes at most one
    canonical directive per call and leaves authoritative review and
    application to `context-compiler`.
    """

    def draft_directive(self, user_input: str, engine: Engine) -> DraftResult:
        """Draft at most one canonical directive from one user input.

        Args:
            user_input: Raw user text to interpret as a possible directive.
            engine: Read-only compiler context used only for deterministic
                refinement decisions. This method does not apply directives or
                mutate authoritative state through the engine.

        Returns:
            A DraftResult containing the explicit drafting outcome and the
            final directive proposal, if one was produced.
        """

        heuristic_result = preprocess_heuristic(user_input)
        drafted = DraftResult(
            outcome=heuristic_result["outcome"],
            directive=heuristic_result["directive"],
        )

        if drafted.directive is None:
            return drafted

        canonical_directive = decompose_directive(drafted.directive)
        assert canonical_directive is not None

        refined = refine_directive(canonical_directive, engine)
        if refined.text == drafted.directive:
            return drafted

        return DraftResult(outcome=drafted.outcome, directive=refined.text)
