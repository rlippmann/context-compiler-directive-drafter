import json
from pathlib import Path

from context_compiler_directive_drafter import (
    parse_preprocessor_output,
    preprocess_heuristic,
    validate_preprocessor_output,
)

_PREPROCESSOR_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "preprocessor"


def _behavior_fixture_paths() -> list[Path]:
    return sorted(path for path in _PREPROCESSOR_FIXTURES_DIR.glob("*.json"))


def _load_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_result(message: str) -> dict[str, object]:
    result = preprocess_heuristic(message)
    output = result["directive"] if result["outcome"] == "directive" else None
    normalized = {
        "classification": result["outcome"],
        "output": output,
    }

    # Enforce the validation boundary: only validated directive output may pass.
    validated = validate_preprocessor_output(output)
    if normalized["classification"] == "directive":
        assert validated["classification"] == "directive"
        assert validated["output"] == output
    else:
        assert output is None
        assert validated["output"] is None

    return normalized


def _normalize_validator_result(raw_output: object) -> dict[str, object]:
    validated = validate_preprocessor_output(raw_output)
    return {
        "classification": validated["classification"],
        "output": validated["output"],
    }


def _normalize_parse_result(raw_output: object) -> str | None:
    return parse_preprocessor_output(raw_output)


def test_preprocessor_conformance_fixtures() -> None:
    for path in _behavior_fixture_paths():
        fixture = _load_fixture(path)
        if path.name.startswith("public-api-"):
            continue

        fixture_name = fixture.get("name", path.name)
        kind = fixture.get("kind", "heuristic")

        if kind == "heuristic":
            expected = fixture.get("expected")
            assert isinstance(expected, dict), fixture_name
            input_text = fixture.get("input")
            assert isinstance(input_text, str), fixture_name

            # Deterministic replay check.
            first = _normalize_result(input_text)
            second = _normalize_result(input_text)
            assert first == second, fixture_name
            assert first == expected, fixture_name
            continue

        assert "raw_output" in fixture, fixture_name
        raw_output = fixture["raw_output"]

        if kind == "validator":
            expected = fixture.get("expected")
            assert isinstance(expected, dict), fixture_name
            # Deterministic replay check.
            first = _normalize_validator_result(raw_output)
            second = _normalize_validator_result(raw_output)
            assert first == second, fixture_name
            assert first == expected, fixture_name
            continue

        assert kind == "parse", fixture_name
        assert "expected_parsed" in fixture, fixture_name
        expected_parsed = fixture["expected_parsed"]
        assert isinstance(expected_parsed, str) or expected_parsed is None, fixture_name

        # Deterministic replay check.
        first_parsed = _normalize_parse_result(raw_output)
        second_parsed = _normalize_parse_result(raw_output)
        assert first_parsed == second_parsed, fixture_name
        assert first_parsed == expected_parsed, fixture_name
