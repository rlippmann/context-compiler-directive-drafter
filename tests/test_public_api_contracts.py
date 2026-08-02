import inspect
import json
from importlib import import_module
from pathlib import Path

from context_compiler import create_engine

import context_compiler_directive_drafter as package

_CONTRACTS_DIR = Path(__file__).resolve().parent / "fixtures" / "contracts"


def _contract_paths() -> list[Path]:
    return sorted(_CONTRACTS_DIR.glob("*.json"))


def _load_contract(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


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
        for variant in shape["any_of"]:
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
        for key, property_shape in shape.get("properties", {}).items():
            if key in value:
                _assert_shape(value[key], property_shape)

    if "enum" in shape:
        assert value in shape["enum"]


def _assert_shape_schema(shape: dict[str, object], label: str) -> None:
    if "any_of" in shape:
        _assert_exact_keys(shape, {"any_of"}, label)
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
    expected_types = shape["type"]
    assert isinstance(expected_types, str | list), label
    if isinstance(expected_types, list):
        assert expected_types and all(isinstance(item, str) for item in expected_types), label

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


def _assert_directive_drafter_behavior_probe_schema(probe: dict[str, object], label: str) -> None:
    _assert_exact_keys(
        probe,
        {"kind", "engine_state", "user_input", "expect_result", "expect_engine_unchanged"},
        label,
    )
    assert probe["kind"] == "directive_drafter_draft", label
    assert isinstance(probe["engine_state"], dict), label
    assert isinstance(probe["user_input"], str), label
    assert isinstance(probe["expect_result"], dict), label
    _assert_shape_schema(probe["expect_result"], f"{label}.expect_result")
    assert isinstance(probe["expect_engine_unchanged"], bool), label


def _assert_export_kind(name: str, exported: object, expected_kind: str) -> None:
    if expected_kind == "callable":
        assert inspect.isroutine(exported), name
        return
    if expected_kind == "constant":
        assert not inspect.isroutine(exported) and not inspect.isclass(exported), name
        return
    if expected_kind in {"type", "class"}:
        assert inspect.isclass(exported), name
        return
    if expected_kind == "type_alias":
        assert not inspect.isroutine(exported) and not inspect.isclass(exported), name
        return
    raise AssertionError(f"Unsupported export kind: {expected_kind!r}")


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
    _assert_exact_keys(
        spec, {"kind"} | ({"public_members", "behavior_probes"} & set(spec.keys())), label
    )
    public_members = spec.get("public_members")
    if public_members is not None:
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
            _assert_signature_schema(
                member_contract["signature"], f"{label}.{member_name}.signature"
            )

    behavior_probes = spec.get("behavior_probes")
    if behavior_probes is not None:
        assert isinstance(behavior_probes, list), f"{label}.behavior_probes"
        for index, probe in enumerate(behavior_probes):
            assert isinstance(probe, dict), f"{label}.behavior_probes[{index}]"
            if probe.get("kind") == "directive_drafter_draft":
                _assert_directive_drafter_behavior_probe_schema(
                    probe, f"{label}.behavior_probes[{index}]"
                )
                continue
            raise AssertionError(f"Unsupported behavior probe for {label}: {probe!r}")


def _assert_render_prompt_behavior_probe(
    exported: object, probe: dict[str, object], tmp_path: Path
) -> None:
    template_path = tmp_path / probe["path"]
    template_path.write_text(probe["template"], encoding="utf-8")
    result = exported(template_path, probe["premise"], probe["policies"])
    assert result == probe["expect_result"]
    for substring in probe.get("reject_substrings", []):
        assert substring not in result


def _assert_directive_drafter_behavior_probe(exported: object, probe: dict[str, object]) -> None:
    engine = create_engine(probe["engine_state"])
    before = engine.state
    drafter = exported()
    result = drafter.draft_directive(probe["user_input"], engine)
    _assert_shape(result.__dict__, probe["expect_result"])
    if probe["expect_engine_unchanged"]:
        assert engine.state == before


def _assert_callable_contract(
    name: str, exported: object, spec: dict[str, object], tmp_path: Path
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


def _assert_class_contract(name: str, exported: object, spec: dict[str, object]) -> None:
    _assert_export_kind(name, exported, "class")

    public_members = spec.get("public_members")
    if public_members is not None:
        members = public_members["members"]
        actual_public_members = sorted(
            member for member in dir(exported) if not member.startswith("_")
        )
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
                getattr(exported, member_name),
                member_contract["signature"],
                f"{name}.{member_name}",
            )

    for probe in spec.get("behavior_probes", []):
        if name == "DirectiveDrafter":
            _assert_directive_drafter_behavior_probe(exported, probe)
            continue
        raise AssertionError(f"Unsupported class behavior probe for {name}: {probe!r}")


def _assert_contract_schema(path: Path, contract: dict[str, object]) -> None:
    label = path.name
    kind = contract.get("kind")
    if kind == "api-surface-contract":
        _assert_exact_keys(
            contract, {"id", "kind", "module", "forbidden_exports", "exports"}, label
        )
        assert isinstance(contract["forbidden_exports"], list), label
        return

    assert kind == "api-capability-contract", label
    _assert_exact_keys(contract, {"id", "kind", "module", "capability", "members"}, label)
    assert isinstance(contract["capability"], str), label
    assert isinstance(contract["members"], dict), label


def _assert_member_specs_schema(members: dict[str, object], label: str) -> None:
    for export_name, export_contract in members.items():
        assert isinstance(export_name, str), f"{label}.members"
        assert isinstance(export_contract, dict), export_name
        kind = export_contract["kind"]
        assert kind in {"callable", "constant", "type_alias", "type", "class"}, export_name
        if kind == "callable":
            _assert_callable_spec_schema(export_contract, export_name)
            continue
        if kind == "constant":
            _assert_exact_keys(export_contract, {"kind", "value"}, export_name)
            continue
        if kind in {"type_alias", "type"}:
            _assert_exact_keys(export_contract, {"kind"}, export_name)
            continue
        _assert_class_spec_schema(export_contract, export_name)


def test_public_api_contract_fixtures_have_valid_schema() -> None:
    for path in _contract_paths():
        contract = _load_contract(path)
        _assert_contract_schema(path, contract)
        if contract["kind"] == "api-surface-contract":
            exports = contract["exports"]
            _assert_exact_keys(exports, {"mode", "names", "members"}, f"{path.name}.exports")
            assert exports["mode"] == "exact", path.name
            assert isinstance(exports["names"], list), path.name
            assert isinstance(exports["members"], dict), path.name
            _assert_member_specs_schema(exports["members"], path.name)
            continue
        _assert_member_specs_schema(contract["members"], path.name)


def test_public_api_surface_contract_matches_package_root_exports() -> None:
    path = _CONTRACTS_DIR / "public-api-v1.json"
    contract = _load_contract(path)
    assert contract["module"] == package.__name__

    exports = contract["exports"]
    expected_exports = exports["names"]
    export_members = exports["members"]

    assert set(package.__all__) == set(expected_exports)
    for name in expected_exports:
        assert hasattr(package, name), name
        assert name in package.__all__, name

    assert set(export_members.keys()) == set(expected_exports)
    for name in contract.get("forbidden_exports", []):
        assert name not in package.__all__, name
        assert not hasattr(package, name), name


def test_public_api_surface_contract_has_unique_entries() -> None:
    path = _CONTRACTS_DIR / "public-api-v1.json"
    contract = _load_contract(path)
    export_names = contract["exports"]["names"]
    assert len(export_names) == len(set(export_names))
    forbidden_exports = contract.get("forbidden_exports", [])
    assert len(forbidden_exports) == len(set(forbidden_exports))
    assert not (set(forbidden_exports) & set(export_names))
    export_member_names = list(contract["exports"]["members"].keys())
    assert len(export_member_names) == len(set(export_member_names))
    assert set(export_member_names) == set(export_names)


def test_public_api_surface_contract_excludes_typing_only_names() -> None:
    path = _CONTRACTS_DIR / "public-api-v1.json"
    contract = _load_contract(path)
    for name in ["DraftOutcome", "PreprocessResult"]:
        assert name not in contract["exports"]["names"], name
        assert name in contract["forbidden_exports"], name
        assert not hasattr(package, name), name
        assert name not in package.__all__, name


def test_public_api_capability_contracts_reference_exported_members_only() -> None:
    for path in _contract_paths():
        contract = _load_contract(path)
        if contract["kind"] != "api-capability-contract":
            continue
        assert contract["module"] == package.__name__, path.name
        for name in contract["members"]:
            assert hasattr(package, name), f"{path.name}:{name}"
            assert name in package.__all__, f"{path.name}:{name}"


def test_public_api_contracts_validate_kinds_signatures_and_shapes(
    tmp_path: Path,
) -> None:
    for path in _contract_paths():
        contract = _load_contract(path)
        members = (
            contract["exports"]["members"]
            if contract["kind"] == "api-surface-contract"
            else contract["members"]
        )
        for name, spec in members.items():
            exported = getattr(package, name)
            kind = spec["kind"]
            _assert_export_kind(name, exported, kind)
            if kind == "callable":
                _assert_callable_contract(name, exported, spec, tmp_path)
                continue
            if kind == "constant":
                assert exported == spec["value"], name
                continue
            if kind == "class":
                _assert_class_contract(name, exported, spec)
                continue
            if kind == "type_alias":
                continue
            raise AssertionError(f"Unsupported contract kind for {name}: {kind}")


def test_public_api_surface_contract_matches_exact_export_set() -> None:
    path = _CONTRACTS_DIR / "public-api-v1.json"
    contract = _load_contract(path)
    assert set(contract["exports"]["names"]) == {
        "PREPROCESSOR_NO_DIRECTIVE_SENTINEL",
        "DRAFT_OUTCOME_DIRECTIVE",
        "DRAFT_OUTCOME_NO_DIRECTIVE",
        "DRAFT_OUTCOME_UNKNOWN",
        "DraftResult",
        "DirectiveDrafter",
        "parse_preprocessor_output",
        "preprocess_heuristic",
        "refine_directive",
        "render_prompt",
        "validate_preprocessor_output",
    }


def test_typing_only_names_are_not_importable_from_package_root() -> None:
    imported = import_module("context_compiler_directive_drafter")
    for name in ["DraftOutcome", "PreprocessResult"]:
        assert name not in imported.__dict__, name


def test_directive_drafter_constructor_supports_optional_fallback() -> None:
    signature = inspect.signature(package.DirectiveDrafter)
    parameters = list(signature.parameters.values())

    assert len(parameters) == 1
    assert parameters[0].name == "fallback"
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[0].default is None
