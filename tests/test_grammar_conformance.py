import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from context_compiler_directive_drafter import heuristic_preprocessor
from context_compiler_directive_drafter.fallbacks import _prompts

pytestmark = pytest.mark.contract

_FIXTURE = Path(__file__).parent / "fixtures" / "grammar" / "grammar-derivation-v1.json"


def _metadata(case: dict[str, object]) -> tuple[SimpleNamespace, ...]:
    return tuple(
        SimpleNamespace(
            kind=record["kind"],
            canonical_start=record["canonical_start"],
            operand_names=tuple(record["operand_names"]),
        )
        for record in case["metadata"]
    )


def test_grammar_dependent_outputs_follow_synthetic_metadata() -> None:
    contract = json.loads(_FIXTURE.read_text(encoding="utf-8"))

    for case in contract["cases"]:
        metadata = _metadata(case)
        categories = {record["kind"]: record["category"] for record in case["metadata"]}

        starts = heuristic_preprocessor._directive_canonical_starts_from_metadata(metadata)
        grammar_section = _prompts._render_canonical_forms_from_metadata(metadata, categories)
        incomplete = case["incomplete"]
        rewrite = case["rewrite"]

        assert list(starts) == case["canonical_starts"]
        assert grammar_section.splitlines()[1:] == case["prompt_forms"]
        for message, expected in incomplete.items():
            assert (
                heuristic_preprocessor._is_incomplete_canonical_directive(message, metadata)
                is expected
            )
        assert (
            heuristic_preprocessor._render_canonical_candidate(
                rewrite["kind"], tuple(rewrite["operands"]), metadata
            )
            == rewrite["expected"]
        )


def test_synthetic_added_directive_changes_both_derived_outputs() -> None:
    contract = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    baseline, added = contract["cases"]

    baseline_metadata = _metadata(baseline)
    added_metadata = _metadata(added)
    baseline_categories = {record["kind"]: record["category"] for record in baseline["metadata"]}
    added_categories = {record["kind"]: record["category"] for record in added["metadata"]}

    baseline_starts = heuristic_preprocessor._directive_canonical_starts_from_metadata(
        baseline_metadata
    )
    added_starts = heuristic_preprocessor._directive_canonical_starts_from_metadata(added_metadata)
    baseline_prompt = _prompts._render_canonical_forms_from_metadata(
        baseline_metadata, baseline_categories
    )
    added_prompt = _prompts._render_canonical_forms_from_metadata(added_metadata, added_categories)
    baseline_rewrite = heuristic_preprocessor._render_canonical_candidate(
        baseline["rewrite"]["kind"],
        tuple(baseline["rewrite"]["operands"]),
        baseline_metadata,
    )
    added_rewrite = heuristic_preprocessor._render_canonical_candidate(
        added["rewrite"]["kind"],
        tuple(added["rewrite"]["operands"]),
        added_metadata,
    )

    assert "adopt" not in baseline_starts
    assert "adopt" in added_starts
    assert "`adopt <rule>` (Policy)" not in baseline_prompt
    assert "`adopt <rule>` (Policy)" in added_prompt
    assert baseline_rewrite == "use docker"
    assert added_rewrite == "adopt strictness"
