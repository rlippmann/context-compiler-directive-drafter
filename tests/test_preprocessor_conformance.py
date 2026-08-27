import json
from pathlib import Path

from context_compiler.grammar import CanonicalDirective

from context_compiler_directive_drafter.heuristic_preprocessor import _preprocess_heuristic
from context_compiler_directive_drafter.output_validation import _classify_drafter_output

preprocess_heuristic = _preprocess_heuristic
classify_drafter_output = _classify_drafter_output

_PREPROCESSOR_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "preprocessor"
_REQUIRED_FIXTURE_FAMILIES = {"heuristic", "validator"}


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
    assert classification in {"directive", "rejected"}, label
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
    assert outcome in {"directive", "rejected", "unknown"}, label
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
    assert kind in {"heuristic", "validator"}, label

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
    validated = classify_drafter_output(output)
    if serialized["outcome"] == "directive":
        assert validated["classification"] == "directive"
        assert validated["output"] == output
    else:
        assert output is None
        assert validated["output"] is None

    return serialized


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
            first = classify_drafter_output(raw_output)
            second = classify_drafter_output(raw_output)
            assert first == second, fixture_name
            assert first == expected, fixture_name
            continue

        raise AssertionError(f"Unsupported preprocessor fixture kind: {kind}")
