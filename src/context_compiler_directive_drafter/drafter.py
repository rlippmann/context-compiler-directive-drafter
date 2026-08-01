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

    user_input: str
    outcome: PreprocessOutcome
    candidate_directive: str | None
    refined_directive: str | None
    rule_id: str | None
    authoritative: bool = False
    rationale: str = ""


class DirectiveDrafter:
    """Minimal synchronous orchestration over the public drafting helpers."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def draft_directive(self, user_input: str) -> DraftResult:
        """Draft at most one canonical directive from one user input."""

        preprocess_result = preprocess_heuristic(user_input)
        outcome = preprocess_result["outcome"]
        candidate_directive = preprocess_result["directive"]
        rule_id = preprocess_result["rule_id"]

        if candidate_directive is None:
            return DraftResult(
                user_input=user_input,
                outcome=outcome,
                candidate_directive=None,
                refined_directive=None,
                rule_id=rule_id,
                rationale=_rationale_for_non_directive_outcome(outcome),
            )

        canonical_directive = decompose_directive(candidate_directive)
        assert canonical_directive is not None

        refined = refine_directive(canonical_directive, self._engine)
        return DraftResult(
            user_input=user_input,
            outcome=outcome,
            candidate_directive=candidate_directive,
            refined_directive=refined.text,
            rule_id=rule_id,
            rationale="Drafted a candidate directive with deterministic refinement.",
        )


def _rationale_for_non_directive_outcome(outcome: PreprocessOutcome) -> str:
    if outcome == "no_directive":
        return "Input did not look like a directive request."
    if outcome == "unknown":
        return "Input was directive-related but too unclear for safe drafting."
    return "Drafting did not produce a directive."
