"""Synchronous orchestration for non-authoritative directive drafting."""

from dataclasses import dataclass

from context_compiler import Engine
from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter.constants import PreprocessOutcome
from context_compiler_directive_drafter.heuristic_preprocessor import preprocess_heuristic
from context_compiler_directive_drafter.refiner import refine_directive


@dataclass(frozen=True)
class DraftResult:
    """Structured non-authoritative result for one drafting attempt."""

    outcome: PreprocessOutcome
    directive: str | None


class DirectiveDrafter:
    """Minimal synchronous orchestration over the public drafting helpers."""

    def draft_directive(self, user_input: str, engine: Engine) -> DraftResult:
        """Draft at most one canonical directive from one user input."""

        preprocess_result = preprocess_heuristic(user_input)
        outcome = preprocess_result["outcome"]
        candidate_directive = preprocess_result["directive"]

        if candidate_directive is None:
            return DraftResult(outcome=outcome, directive=None)

        canonical_directive = decompose_directive(candidate_directive)
        assert canonical_directive is not None

        refined = refine_directive(canonical_directive, engine)
        return DraftResult(outcome=outcome, directive=refined.text)
