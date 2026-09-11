import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from context_compiler_directive_drafter.fallbacks import _prompts

pytestmark = pytest.mark.contract

_FIXTURE = Path(__file__).parent / "fixtures" / "prompts" / "prompt-construction-v1.json"


def _metadata(case: dict[str, object]) -> tuple[SimpleNamespace, ...]:
    return tuple(
        SimpleNamespace(
            kind=record["kind"],
            canonical_start=record["canonical_start"],
            operand_names=tuple(record["operand_names"]),
        )
        for record in case["metadata"]
    )


def _examples(case: dict[str, object]) -> tuple[SimpleNamespace, ...]:
    return tuple(
        SimpleNamespace(
            kind=record["kind"],
            user_input=record["user_input"],
            operand_values=tuple(record["operand_values"]),
        )
        for record in case["positive_examples"]
    )


def _contrasts(case: dict[str, object]) -> tuple[SimpleNamespace, ...]:
    return tuple(
        SimpleNamespace(
            kind=record["kind"],
            user_input=record["user_input"],
            operand_values=tuple(record["operand_values"]),
            truncated_operand_values=tuple(record["truncated_operand_values"]),
        )
        for record in case["scope_payload_contrasts"]
    )


def test_prompt_construction_follows_synthetic_portable_inputs() -> None:
    contract = json.loads(_FIXTURE.read_text(encoding="utf-8"))

    for case in contract["cases"]:
        metadata = _metadata(case)
        categories = {record["kind"]: record["category"] for record in case["metadata"]}
        allowed = case["allowed_directive_kinds"]
        allowed_kinds = None if allowed is None else frozenset(allowed)
        prompt = _prompts._render_prompt_from_construction(
            case["mode"],
            metadata,
            categories,
            _examples(case),
            _contrasts(case),
            allowed_kinds,
        )
        expected = case["expected"]

        for substring in expected["canonical_forms"]:
            assert substring in prompt, case["name"]
        for substring in expected["positive_examples"]:
            assert substring in prompt, case["name"]
        for substring in expected["scope_payload_contrasts"]:
            assert substring in prompt, case["name"]
        for substring in expected["kind_restriction"] or []:
            assert substring in prompt, case["name"]
        for substring in expected["required_substrings"]:
            assert substring in prompt, case["name"]
        for substring in expected["forbidden_substrings"]:
            assert substring not in prompt, case["name"]


def test_synthetic_prompt_construction_cannot_use_current_golden_inventory() -> None:
    contract = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    free_text = contract["cases"][0]
    prompt = _prompts._render_prompt_from_construction(
        free_text["mode"],
        _metadata(free_text),
        {record["kind"]: record["category"] for record in free_text["metadata"]},
        _examples(free_text),
        _contrasts(free_text),
    )

    assert "`adopt <rule>` (Policy)" in prompt
    assert "User: please adopt strictness" in prompt
    assert "Correct candidate: adopt strictness for release" in prompt
