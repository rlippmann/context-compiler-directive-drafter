import inspect
import json
from importlib import import_module
from pathlib import Path

import context_compiler_directive_drafter as preprocessor

_CONTRACT_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "preprocessor" / "public-api-v1.json"
)


def _load_contract() -> dict[str, object]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


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

    if "const" in shape:
        assert value == shape["const"]

    if isinstance(value, dict):
        required_keys = shape.get("required_keys", [])
        assert set(required_keys).issubset(value)
        properties = shape.get("properties", {})
        for key, property_shape in properties.items():
            if key in value:
                _assert_shape(value[key], property_shape)

    if "enum" in shape:
        assert value in shape["enum"]


def _assert_signature_matches(obj: object, expected: dict[str, object], label: str) -> None:
    signature = inspect.signature(obj)
    params = list(signature.parameters.values())
    expected_params = expected["params"]

    assert len(params) == len(expected_params), label
    for actual, expected_param in zip(params, expected_params, strict=True):
        assert actual.name == expected_param["name"], label
        assert actual.kind.name == expected_param["kind"], label
        assert (actual.default is not inspect.Signature.empty) is expected_param["has_default"], (
            label
        )


def _assert_render_prompt_behavior_probe(
    exported: object, probe: dict[str, object], tmp_path: Path
) -> None:
    assert probe["kind"] == "render_prompt_from_file"

    template_path = tmp_path / probe["path"]
    template_path.write_text(probe["template"], encoding="utf-8")

    result = exported(template_path, probe["premise"], probe["policies"])
    assert result == probe["expect_result"]
    for substring in probe.get("reject_substrings", []):
        assert substring not in result


def _assert_export_kind(name: str, exported: object, expected_kind: str) -> None:
    if expected_kind == "callable":
        assert inspect.isroutine(exported), name
        return
    if expected_kind == "constant":
        assert not inspect.isroutine(exported) and not inspect.isclass(exported), name
        return
    if expected_kind == "type_alias":
        assert not inspect.isroutine(exported) and not inspect.isclass(exported), name
        return
    assert expected_kind == "class", name
    assert inspect.isclass(exported), name


def _assert_callable_contract(
    name: str,
    exported: object,
    spec: dict[str, object],
    tmp_path: Path,
) -> None:
    _assert_signature_matches(exported, spec["signature"], name)

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
    assert exported == spec["value"], name


def _assert_class_contract(name: str, exported: object, spec: dict[str, object]) -> None:
    _assert_export_kind(name, exported, "class")

    public_members = spec.get("public_members")
    if public_members is None:
        return

    members = public_members["members"]
    actual_public_members = sorted(member for member in dir(exported) if not member.startswith("_"))
    assert actual_public_members == sorted(members.keys()), name

    for member_name, member_contract in members.items():
        assert hasattr(exported, member_name), f"{name}.{member_name}"
        kind = member_contract["kind"]
        descriptor = inspect.getattr_static(exported, member_name)

        if kind == "property":
            assert isinstance(descriptor, property), f"{name}.{member_name}"
            continue

        assert callable(getattr(exported, member_name)), f"{name}.{member_name}"
        _assert_signature_matches(
            getattr(exported, member_name), member_contract["signature"], (f"{name}.{member_name}")
        )


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
    exports = contract["exports"]
    expected_exports = exports["names"]
    export_members = exports["members"]

    assert set(expected_exports) == set(_EXPECTED_RUNTIME_EXPORTS)
    if contract["forbid_additional_public_exports"]:
        assert set(preprocessor.__all__) == set(expected_exports)

    for name in expected_exports:
        assert hasattr(preprocessor, name), name
        assert name in preprocessor.__all__, name

    assert set(export_members.keys()) == set(expected_exports)


def test_preprocessor_api_contract_fixture_has_unique_entries() -> None:
    contract = _load_contract()

    export_names = contract["exports"]["names"]
    assert len(export_names) == len(set(export_names))

    forbidden_exports = contract.get("forbidden_exports", [])
    assert len(forbidden_exports) == len(set(forbidden_exports))
    assert not (set(forbidden_exports) & set(export_names))

    export_member_names = list(contract["exports"]["members"].keys())
    assert len(export_member_names) == len(set(export_member_names))
    assert set(export_member_names) == set(export_names)


def test_preprocessor_api_contract_fixture_excludes_typing_only_names() -> None:
    contract = _load_contract()

    for name in _TYPING_ONLY_NAMES:
        assert name not in contract["exports"]["names"], name
        assert name in contract["forbidden_exports"], name


def test_preprocessor_module_does_not_export_typing_only_names() -> None:
    for name in _TYPING_ONLY_NAMES:
        assert not hasattr(preprocessor, name), name
        assert name not in preprocessor.__all__, name


def test_expected_runtime_exports_match_contract_exactly() -> None:
    contract = _load_contract()

    assert set(_EXPECTED_RUNTIME_EXPORTS) == set(contract["exports"]["names"])


def test_typing_only_names_are_not_importable_from_package_root() -> None:
    package = import_module("context_compiler_directive_drafter")

    for name in _TYPING_ONLY_NAMES:
        assert name not in package.__dict__, name


def test_preprocessor_api_contract_fixture_declares_core_style_export_schema() -> None:
    contract = _load_contract()

    exports = contract["exports"]
    assert exports["mode"] == "exact"

    for export_name, export_contract in exports["members"].items():
        kind = export_contract["kind"]
        assert kind in {"callable", "constant", "type_alias", "class"}, export_name
        if kind == "callable":
            assert "signature" in export_contract, export_name
        else:
            assert "signature" not in export_contract, export_name

        if kind == "class":
            public_members = export_contract.get("public_members")
            if public_members is None:
                continue
            assert public_members["mode"] == "exact", export_name
            for member_name, member_contract in public_members["members"].items():
                member_kind = member_contract["kind"]
                assert member_kind in {"method", "property"}, f"{export_name}.{member_name}"
                if member_kind == "property":
                    assert "signature" not in member_contract, f"{export_name}.{member_name}"
                else:
                    assert "signature" in member_contract, f"{export_name}.{member_name}"


def test_preprocessor_api_contract_fixture_validates_export_kinds_signatures_and_shapes(
    tmp_path: Path,
) -> None:
    contract = _load_contract()

    for name, spec in contract["exports"]["members"].items():
        exported = getattr(preprocessor, name)
        kind = spec["kind"]

        _assert_export_kind(name, exported, kind)

        if kind == "callable":
            _assert_callable_contract(name, exported, spec, tmp_path)
            continue
        if kind == "constant":
            _assert_constant_contract(name, exported, spec)
            continue
        if kind == "class":
            _assert_class_contract(name, exported, spec)
            continue
        if kind == "type_alias":
            continue
        raise AssertionError(f"Unsupported contract kind for {name}: {kind}")


def test_preprocessor_api_contract_fixture_forbidden_exports_are_not_present() -> None:
    contract = _load_contract()

    for name in contract.get("forbidden_exports", []):
        assert name not in preprocessor.__all__, name
        assert not hasattr(preprocessor, name), name
