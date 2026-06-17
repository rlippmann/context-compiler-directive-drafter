import json
from importlib import import_module
from inspect import Parameter, isroutine, signature
from pathlib import Path

from context_compiler import create_engine

import context_compiler_directive_drafter as preprocessor

_CONTRACT_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "preprocessor" / "public-api-v1.json"
)


def _load_contract() -> dict[str, object]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


_PARAMETER_KIND_BY_NAME = {
    "positional_only": Parameter.POSITIONAL_ONLY,
    "positional_or_keyword": Parameter.POSITIONAL_OR_KEYWORD,
    "var_positional": Parameter.VAR_POSITIONAL,
    "keyword_only": Parameter.KEYWORD_ONLY,
    "var_keyword": Parameter.VAR_KEYWORD,
}


def _json_type_matches(value: object, expected: str) -> bool:
    return {
        "null": value is None,
        "string": isinstance(value, str),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "boolean": isinstance(value, bool),
        "number": isinstance(value, int | float) and not isinstance(value, bool),
    }[expected]


def _assert_shape(value: object, shape: dict[str, object]) -> None:
    if "any_of" in shape:
        variants = shape["any_of"]
        for variant in variants:
            try:
                _assert_shape(value, variant)
                return
            except AssertionError:
                continue
        raise AssertionError(f"Value did not match any allowed shape: {value!r}")

    expected_types = shape["type"]
    if isinstance(expected_types, str):
        expected_types = [expected_types]
    assert any(_json_type_matches(value, expected_type) for expected_type in expected_types)

    if isinstance(value, dict):
        required_keys = shape.get("required_keys", [])
        assert set(required_keys).issubset(value)
        properties = shape.get("properties", {})
        for key, property_shape in properties.items():
            if key in value:
                _assert_shape(value[key], property_shape)

    if "enum" in shape:
        assert value in shape["enum"]


def _assert_render_prompt_behavior_probe(
    exported: object, probe: dict[str, object], tmp_path: Path
) -> None:
    assert probe["kind"] == "render_prompt_from_file"

    template_path = tmp_path / probe["path"]
    template_path.write_text(probe["template"], encoding="utf-8")

    engine = create_engine()
    for step in probe.get("state_steps", []):
        engine.step(step)

    result = exported(template_path, engine.state)
    assert result == probe["expect_result"]
    for substring in probe.get("reject_substrings", []):
        assert substring not in result


def _assert_callable_contract(
    name: str,
    exported: object,
    spec: dict[str, object],
    tmp_path: Path,
) -> None:
    assert isroutine(exported), name

    actual_parameters = list(signature(exported).parameters.values())
    expected_parameters = spec["parameters"]
    assert len(actual_parameters) == len(expected_parameters), name

    for actual, expected in zip(actual_parameters, expected_parameters, strict=True):
        assert actual.name == expected["name"], name
        assert actual.kind == _PARAMETER_KIND_BY_NAME[expected["kind"]], name
        assert (actual.default is Parameter.empty) == expected["required"], name

    for probe in spec.get("shape_probes", []):
        kwargs = probe["kwargs"]
        assert isinstance(kwargs, dict), name
        result = exported(**kwargs)
        return_shape = spec.get("return_shape")
        if return_shape is not None:
            _assert_shape(result, return_shape)

    for probe in spec.get("behavior_probes", []):
        if name == "render_prompt":
            _assert_render_prompt_behavior_probe(exported, probe, tmp_path)
            continue
        raise AssertionError(f"Unsupported behavior probe for {name}: {probe!r}")


def _assert_constant_contract(name: str, exported: object, spec: dict[str, object]) -> None:
    assert not isroutine(exported), name
    assert exported == spec["value"], name


_EXPECTED_RUNTIME_EXPORTS = [
    "PREPROCESSOR_NO_DIRECTIVE_SENTINEL",
    "PREPROCESS_OUTCOME_DIRECTIVE",
    "PREPROCESS_OUTCOME_NO_DIRECTIVE",
    "PREPROCESS_OUTCOME_UNKNOWN",
    "preprocess_heuristic",
    "validate_preprocessor_output",
    "parse_preprocessor_output",
    "render_prompt",
]

_TYPING_ONLY_NAMES = [
    "PreprocessOutcome",
    "PreprocessResult",
]


def test_preprocessor_api_contract_fixture_matches_public_surface() -> None:
    contract = _load_contract()

    assert contract["kind"] == "api-contract"
    assert set(contract["required_exports"]) == set(_EXPECTED_RUNTIME_EXPORTS)
    if contract["forbid_additional_public_exports"]:
        assert set(preprocessor.__all__) == set(contract["required_exports"])

    for name in contract["required_exports"]:
        assert hasattr(preprocessor, name), name
        assert name in preprocessor.__all__, name


def test_preprocessor_api_contract_fixture_has_unique_entries() -> None:
    contract = _load_contract()

    required_exports = contract["required_exports"]
    assert len(required_exports) == len(set(required_exports))


def test_preprocessor_api_contract_fixture_excludes_typing_only_names() -> None:
    contract = _load_contract()

    for name in _TYPING_ONLY_NAMES:
        assert name not in contract["required_exports"], name
        assert name in contract["forbidden_exports"], name


def test_preprocessor_module_does_not_export_typing_only_names() -> None:
    for name in _TYPING_ONLY_NAMES:
        assert not hasattr(preprocessor, name), name
        assert name not in preprocessor.__all__, name


def test_expected_runtime_exports_match_contract_exactly() -> None:
    contract = _load_contract()

    assert set(_EXPECTED_RUNTIME_EXPORTS) == set(contract["required_exports"])


def test_typing_only_names_are_not_importable_from_package_root() -> None:
    package = import_module("context_compiler_directive_drafter")

    for name in _TYPING_ONLY_NAMES:
        assert name not in package.__dict__, name


def test_preprocessor_api_contract_fixture_describes_all_required_exports() -> None:
    contract = _load_contract()

    export_specs = contract["exports"]
    assert set(export_specs) == set(contract["required_exports"])


def test_preprocessor_api_contract_fixture_validates_export_kinds_signatures_and_shapes(
    tmp_path: Path,
) -> None:
    contract = _load_contract()

    for name, spec in contract["exports"].items():
        exported = getattr(preprocessor, name)
        kind = spec["kind"]
        if kind == "callable":
            _assert_callable_contract(name, exported, spec, tmp_path)
            continue
        if kind == "constant":
            _assert_constant_contract(name, exported, spec)
            continue
        raise AssertionError(f"Unsupported contract kind for {name}: {kind}")
