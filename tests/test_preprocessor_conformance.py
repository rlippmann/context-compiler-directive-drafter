import json
from pathlib import Path

import pytest
from context_compiler.grammar import CanonicalDirective

from context_compiler_directive_drafter import (
    parse_preprocessor_output,
    preprocess_heuristic,
    validate_preprocessor_output,
)

_PREPROCESSOR_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "preprocessor"
_REQUIRED_FIXTURE_FAMILIES = {"heuristic", "validator", "parse"}

pytestmark = pytest.mark.contract


def _behavior_fixture_paths() -> list[Path]:
    return sorted(path for path in _PREPROCESSOR_FIXTURES_DIR.glob("*.json"))


def _load_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_exact_keys(payload: dict[str, object], expected: set[str], label: str) -> None:
    assert set(payload.keys()) == expected, label


def _assert_public_data_attributes(value: object, expected: set[str]) -> None:
    actual = {
        name
        for name in dir(value)
        if not name.startswith("_") and not callable(getattr(value, name))
    }
    assert actual == expected, value


def _assert_validation_expected_contract(expected: object, label: str) -> None:
    assert isinstance(expected, dict), label
    _assert_exact_keys(expected, {"classification", "output"}, label)
    classification = expected["classification"]
    output = expected["output"]
    assert classification in {"directive", "no_directive", "unknown"}, label
    assert isinstance(output, str) or output is None, label
    if classification == "directive":
        assert isinstance(output, str), label
    else:
        assert output is None, label


def _assert_heuristic_expected_contract(expected: object, label: str) -> None:
    assert isinstance(expected, dict), label
    _assert_exact_keys(expected, {"outcome", "directive"} | ({"reason"} & set(expected)), label)
    outcome = expected["outcome"]
    directive = expected["directive"]
    assert outcome in {"directive", "no_directive", "unknown"}, label
    if outcome == "directive":
        assert isinstance(directive, dict), label
        _assert_exact_keys(directive, {"text", "kind", "operands"}, label)
        assert isinstance(directive["text"], str), label
        assert isinstance(directive["kind"], str), label
        assert isinstance(directive["operands"], dict), label
    else:
        assert directive is None, label
        assert isinstance(expected.get("reason"), str), label


def _assert_behavior_fixture_schema(path: Path, fixture: dict[str, object]) -> None:
    label = path.name
    name = fixture.get("name")
    assert isinstance(name, str), label
    assert name == path.stem, label

    kind = fixture.get("kind", "heuristic")
    assert kind in {"heuristic", "validator", "parse"}, label

    if kind == "heuristic":
        _assert_exact_keys(
            fixture, {"name", "input", "expected"} | ({"kind"} & set(fixture.keys())), label
        )
        assert isinstance(fixture["input"], str), label
        _assert_heuristic_expected_contract(fixture["expected"], label)
        return

    if kind == "validator":
        _assert_exact_keys(fixture, {"name", "kind", "raw_output", "expected"}, label)
        _assert_validation_expected_contract(fixture["expected"], label)
        return

    _assert_exact_keys(fixture, {"name", "kind", "raw_output", "expected_parsed"}, label)
    expected_parsed = fixture["expected_parsed"]
    assert isinstance(expected_parsed, dict) or expected_parsed is None, label


def _serialize_heuristic_result(message: str) -> dict[str, object]:
    result = preprocess_heuristic(message)
    if set(result) == {"outcome", "directive"}:
        assert result["outcome"] == "directive"
        assert isinstance(result["directive"], CanonicalDirective)
        _assert_public_data_attributes(result["directive"], {"text", "kind", "operands"})
        output = result["directive"].text
    else:
        assert set(result) == {"outcome", "directive", "reason"}
        assert result["directive"] is None
        output = None

    if result["outcome"] == "directive":
        directive = result["directive"]
        serialized = {
            "outcome": result["outcome"],
            "directive": {
                "text": directive.text,
                "kind": directive.kind.value,
                "operands": dict(directive.operands),
            },
        }
    else:
        serialized = {
            "outcome": result["outcome"],
            "directive": None,
            "reason": result["reason"],
        }

    # Enforce the validation boundary: only validated directive output may pass.
    validated = validate_preprocessor_output(output)
    if serialized["outcome"] == "directive":
        assert validated["classification"] == "directive"
        assert validated["output"] == output
    else:
        assert output is None
        assert validated["output"] is None

    return serialized


def _serialize_parse_result(raw_output: object) -> dict[str, object] | None:
    parsed = parse_preprocessor_output(raw_output)
    if parsed is None:
        return None
    return {
        "text": parsed.text,
        "kind": parsed.kind.value,
        "operands": dict(parsed.operands),
    }


def _fixture_families(paths: list[Path]) -> set[str]:
    families = set()
    for path in paths:
        if path.name.startswith("public-api-"):
            continue
        fixture = _load_fixture(path)
        families.add(fixture.get("kind", "heuristic"))
    return families


def test_preprocessor_conformance_fixtures() -> None:
    paths = _behavior_fixture_paths()
    assert _fixture_families(paths) >= _REQUIRED_FIXTURE_FAMILIES

    for path in paths:
        fixture = _load_fixture(path)
        if path.name.startswith("public-api-"):
            continue

        _assert_behavior_fixture_schema(path, fixture)

        fixture_name = fixture.get("name", path.name)
        kind = fixture.get("kind", "heuristic")

        if kind == "heuristic":
            expected = fixture.get("expected")
            _assert_heuristic_expected_contract(expected, fixture_name)
            input_text = fixture.get("input")
            assert isinstance(input_text, str), fixture_name

            # Deterministic replay check.
            first = _serialize_heuristic_result(input_text)
            second = _serialize_heuristic_result(input_text)
            assert first == second, fixture_name
            assert first == expected, fixture_name
            continue

        assert "raw_output" in fixture, fixture_name
        raw_output = fixture["raw_output"]

        if kind == "validator":
            expected = fixture.get("expected")
            _assert_validation_expected_contract(expected, fixture_name)
            # Deterministic replay check.
            first = validate_preprocessor_output(raw_output)
            second = validate_preprocessor_output(raw_output)
            assert first == second, fixture_name
            assert first == expected, fixture_name
            continue

        assert kind == "parse", fixture_name
        assert "expected_parsed" in fixture, fixture_name
        expected_parsed = fixture["expected_parsed"]
        assert isinstance(expected_parsed, dict) or expected_parsed is None, fixture_name

        # Deterministic replay check.
        first_parsed = _serialize_parse_result(raw_output)
        second_parsed = _serialize_parse_result(raw_output)
        assert first_parsed == second_parsed, fixture_name
        assert first_parsed == expected_parsed, fixture_name
