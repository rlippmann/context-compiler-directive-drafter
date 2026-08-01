"""Regression coverage for the synchronous drafter orchestration layer."""

from context_compiler import create_engine

from context_compiler_directive_drafter import DirectiveDrafter
from context_compiler_directive_drafter.drafter import draft_directive


def test_draft_directive_requires_engine_for_refinement() -> None:
    result = draft_directive("please make replies concise")

    assert result.user_input == "please make replies concise"
    assert result.outcome == "unknown"
    assert result.candidate_directive is None
    assert result.refined_directive is None
    assert result.rule_id is None
    assert result.authoritative is False
    assert result.rationale == "Drafting orchestration requires an engine for refinement."


def test_directive_drafter_returns_refined_candidate_when_heuristic_matches() -> None:
    engine = create_engine({"premise": None, "policies": {}, "version": 2})

    result = DirectiveDrafter(engine).draft_directive("set premise concise replies")

    assert result.user_input == "set premise concise replies"
    assert result.outcome == "directive"
    assert result.candidate_directive == "set premise concise replies"
    assert result.refined_directive == "set premise concise replies"
    assert result.rule_id == "canonical.full_match"
    assert result.authoritative is False


def test_directive_drafter_returns_non_directive_outcome_without_refinement() -> None:
    engine = create_engine({"premise": None, "policies": {}, "version": 2})

    result = DirectiveDrafter(engine).draft_directive("can you help with lunch?")

    assert result.outcome == "no_directive"
    assert result.candidate_directive is None
    assert result.refined_directive is None
    assert result.rule_id == "reject.confident_non_directive"
