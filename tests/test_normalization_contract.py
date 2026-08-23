import json
from pathlib import Path

from context_compiler.grammar import CanonicalDirective

from context_compiler_directive_drafter import (
    parse_preprocessor_output,
    preprocess_heuristic,
    validate_preprocessor_output,
)

_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "normalization-v1.json"


def _load_fixture() -> dict[str, object]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _serialize_directive(value: CanonicalDirective) -> dict[str, object]:
    return {
        "text": value.text,
        "kind": value.kind.value,
        "operands": dict(value.operands),
    }


def _serialize_heuristic_result(input_text: str) -> dict[str, object]:
    result = preprocess_heuristic(input_text)
    if result["outcome"] == "directive":
        return {
            "outcome": result["outcome"],
            "directive": _serialize_directive(result["directive"]),
        }
    return {
        "outcome": result["outcome"],
        "directive": None,
        "reason": result["reason"],
    }


def _serialize_parse_result(input_text: str) -> dict[str, object] | None:
    result = parse_preprocessor_output(input_text)
    return None if result is None else _serialize_directive(result)


def test_normalization_fixture_schema_and_python_behavior() -> None:
    fixture = _load_fixture()
    assert fixture["id"] == "drafter-normalization-v1"
    cases = fixture["cases"]
    assert isinstance(cases, list) and cases

    seen_surfaces: dict[str, set[str]] = {}
    for case in cases:
        assert set(case) == {"name", "surface", "rule", "polarity", "input", "expected"}
        assert case["surface"] in {"heuristic", "validator", "parse"}
        assert case["polarity"] in {"accept", "reject"}
        assert isinstance(case["input"], str)
        seen_surfaces.setdefault(case["surface"], set()).add(case["polarity"])

        if case["surface"] == "heuristic":
            actual = _serialize_heuristic_result(case["input"])
        elif case["surface"] == "validator":
            actual = validate_preprocessor_output(case["input"])
        else:
            actual = _serialize_parse_result(case["input"])
        assert actual == case["expected"], case["name"]

    assert all(polarities == {"accept", "reject"} for polarities in seen_surfaces.values())
