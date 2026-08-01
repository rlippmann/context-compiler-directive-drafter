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


def _assert_exact_keys(payload: dict[str, object], expected: set[str], label: str) -> None:
    assert set(payload.keys()) == expected, label


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


def _assert_shape_schema(shape: dict[str, object], label: str) -> None:
    if "any_of" in shape:
        _assert_exact_keys(shape, {"any_of"}, label)
        assert set(shape.keys()) == {"any_of"}, label
        variants = shape["any_of"]
        assert isinstance(variants, list) and variants, label
        for index, variant in enumerate(variants):
            assert isinstance(variant, dict), f"{label}.any_of[{index}]"
            _assert_shape_schema(variant, f"{label}.any_of[{index}]")
        return

    _assert_exact_keys(
        shape,
        {"type"} | ({"required_keys", "properties", "enum", "const"} & set(shape.keys())),
        label,
    )

    expected_types = shape.get("type")
    assert isinstance(expected_types, str | list), label
    if isinstance(expected_types, list):
        assert expected_types, label
        assert all(isinstance(item, str) for item in expected_types), label

    required_keys = shape.get("required_keys")
    if required_keys is not None:
        assert isinstance(required_keys, list), label
        assert all(isinstance(item, str) for item in required_keys), label

    properties = shape.get("properties")
    if properties is not None:
        assert isinstance(properties, dict), label
        for key, property_shape in properties.items():
            assert isinstance(key, str), label
            assert isinstance(property_shape, dict), f"{label}.properties.{key}"
            _assert_shape_schema(property_shape, f"{label}.properties.{key}")

    enum_values = shape.get("enum")
    if enum_values is not None:
        assert isinstance(enum_values, list), label


def _assert_signature_matches(obj: object, expected: dict[str, object], label: str) -> None:
    expected_is_async = expected["is_async"]
    assert isinstance(expected_is_async, bool), label
    actual_is_async = inspect.iscoroutinefunction(obj) or inspect.isasyncgenfunction(obj)
    assert actual_is_async is expected_is_async, label

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
    _assert_render_prompt_behavior_probe_schema(probe, "render_prompt behavior probe")

    template_path = tmp_path / probe["path"]
    template_path.write_text(probe["template"], encoding="utf-8")

    result = exported(template_path, probe["premise"], probe["policies"])
    assert result == probe["expect_result"]
    for substring in probe.get("reject_substrings", []):
        assert substring not in result


def _assert_render_prompt_behavior_probe_schema(probe: dict[str, object], label: str) -> None:
    _assert_exact_keys(
        probe,
        {"kind", "path", "template", "premise", "policies", "expect_result"}
        | ({"reject_substrings"} & set(probe.keys())),
        label,
    )
    assert probe["kind"] == "render_prompt_from_file"
    assert isinstance(probe["path"], str)
    assert isinstance(probe["template"], str)
    assert probe["premise"] is None or isinstance(probe["premise"], str)
    assert isinstance(probe["policies"], dict)
    assert isinstance(probe["expect_result"], str)
    reject_substrings = probe.get("reject_substrings", [])
    assert isinstance(reject_substrings, list)
    assert all(isinstance(item, str) for item in reject_substrings)


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
    if expected_kind == "type":
        assert inspect.isclass(exported), name
        return
    assert expected_kind == "class", name
    assert inspect.isclass(exported), name


def _assert_signature_schema(signature_spec: dict[str, object], label: str) -> None:
    _assert_exact_keys(signature_spec, {"is_async", "params"}, label)
    assert isinstance(signature_spec["is_async"], bool), label
    params = signature_spec["params"]
    assert isinstance(params, list), label
    for index, parameter in enumerate(params):
        assert isinstance(parameter, dict), f"{label}.params[{index}]"
        _assert_exact_keys(parameter, {"name", "kind", "has_default"}, f"{label}.params[{index}]")
        assert isinstance(parameter["name"], str), f"{label}.params[{index}]"
        assert parameter["kind"] in {
            "POSITIONAL_ONLY",
            "POSITIONAL_OR_KEYWORD",
            "VAR_POSITIONAL",
            "KEYWORD_ONLY",
            "VAR_KEYWORD",
        }, f"{label}.params[{index}]"
        assert isinstance(parameter["has_default"], bool), f"{label}.params[{index}]"


def _assert_callable_spec_schema(spec: dict[str, object], label: str) -> None:
    _assert_exact_keys(
        spec,
        {"kind", "signature"}
        | ({"return_shape"} & set(spec.keys()))
        | ({"shape_probes"} & set(spec.keys()))
        | ({"behavior_probes"} & set(spec.keys())),
        label,
    )
    _assert_signature_schema(spec["signature"], f"{label}.signature")

    if "return_shape" in spec:
        assert isinstance(spec["return_shape"], dict), f"{label}.return_shape"
        _assert_shape_schema(spec["return_shape"], f"{label}.return_shape")

    if "shape_probes" in spec:
        shape_probes = spec["shape_probes"]
        assert isinstance(shape_probes, list), f"{label}.shape_probes"
        for index, probe in enumerate(shape_probes):
            assert isinstance(probe, dict), f"{label}.shape_probes[{index}]"
            _assert_exact_keys(probe, {"kwargs"}, f"{label}.shape_probes[{index}]")
            assert isinstance(probe["kwargs"], dict), f"{label}.shape_probes[{index}]"

    if "behavior_probes" in spec:
        behavior_probes = spec["behavior_probes"]
        assert isinstance(behavior_probes, list), f"{label}.behavior_probes"
        for index, probe in enumerate(behavior_probes):
            assert isinstance(probe, dict), f"{label}.behavior_probes[{index}]"
            if probe.get("kind") == "render_prompt_from_file":
                _assert_render_prompt_behavior_probe_schema(
                    probe, f"{label}.behavior_probes[{index}]"
                )
                continue
            raise AssertionError(f"Unsupported behavior probe for {label}: {probe!r}")


def _assert_class_spec_schema(spec: dict[str, object], label: str) -> None:
    _assert_exact_keys(spec, {"kind"} | ({"public_members"} & set(spec.keys())), label)
    public_members = spec.get("public_members")
    if public_members is None:
        return

    assert isinstance(public_members, dict), f"{label}.public_members"
    _assert_exact_keys(public_members, {"mode", "members"}, f"{label}.public_members")
    assert public_members["mode"] == "exact", f"{label}.public_members"
    members = public_members["members"]
    assert isinstance(members, dict), f"{label}.public_members.members"

    for member_name, member_contract in members.items():
        assert isinstance(member_name, str), f"{label}.public_members.members"
        assert isinstance(member_contract, dict), f"{label}.{member_name}"
        member_kind = member_contract.get("kind")
        assert member_kind in {"method", "property"}, f"{label}.{member_name}"
        if member_kind == "property":
            _assert_exact_keys(member_contract, {"kind"}, f"{label}.{member_name}")
            continue
        _assert_exact_keys(member_contract, {"kind", "signature"}, f"{label}.{member_name}")
        _assert_signature_schema(member_contract["signature"], f"{label}.{member_name}.signature")


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
    "DirectiveDrafter",
    "preprocess_heuristic",
    "validate_preprocessor_output",
    "parse_preprocessor_output",
    "refine_directive",
    "render_prompt",
]

_TYPING_ONLY_NAMES = [
    "PreprocessOutcome",
    "PreprocessResult",
]


def test_preprocessor_api_contract_fixture_matches_public_surface() -> None:
    contract = _load_contract()

    _assert_exact_keys(
        contract, {"id", "kind", "module", "forbidden_exports", "exports"}, "contract"
    )
    assert contract["kind"] == "api-contract"
    assert contract["module"] == preprocessor.__name__
    exports = contract["exports"]
    expected_exports = exports["names"]
    export_members = exports["members"]

    assert set(expected_exports) == set(_EXPECTED_RUNTIME_EXPORTS)
    if exports["mode"] == "exact":
        assert set(preprocessor.__all__) == set(expected_exports)
    else:
        raise AssertionError(f"Unsupported exports mode: {exports['mode']!r}")

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
    _assert_exact_keys(exports, {"mode", "names", "members"}, "exports")
    assert isinstance(exports["names"], list)
    assert all(isinstance(name, str) for name in exports["names"])
    assert isinstance(exports["members"], dict)

    for export_name, export_contract in exports["members"].items():
        assert isinstance(export_name, str), "exports.members"
        assert isinstance(export_contract, dict), export_name
        kind = export_contract["kind"]
        assert kind in {"callable", "constant", "type_alias", "type", "class"}, export_name
        if kind == "callable":
            _assert_callable_spec_schema(export_contract, export_name)
            continue
        if kind == "constant":
            _assert_exact_keys(export_contract, {"kind", "value"}, export_name)
            continue
        if kind == "type_alias":
            _assert_exact_keys(export_contract, {"kind"}, export_name)
            continue
        if kind == "type":
            _assert_exact_keys(export_contract, {"kind"}, export_name)
            continue
        _assert_class_spec_schema(export_contract, export_name)


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
