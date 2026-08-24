import inspect
import json
from importlib import import_module
from pathlib import Path

import pytest
from context_compiler.grammar import CanonicalDirective

import context_compiler_directive_drafter as package
from context_compiler_directive_drafter.drafter import DraftResult, NoDirective, UnknownDirective

_CONTRACTS_DIR = Path(__file__).resolve().parent / "fixtures" / "contracts"
_REQUIRED_CONTRACT_FILES = {
    "acquisition-v1.json",
    "high-level-drafting-v1.json",
    "grammar-v1.json",
    "prompt-rendering-v1.json",
    "public-api-v1.json",
    "validation-v1.json",
}

pytestmark = pytest.mark.contract


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
        properties = shape.get("properties", {})
        if properties:
            assert set(value) == set(required_keys) | set(properties)
        for key, property_shape in properties.items():
            if key in value:
                _assert_shape(value[key], property_shape)

    if "enum" in shape:
        assert value in shape["enum"]


def _assert_public_data_attributes(value: object, expected: set[str]) -> None:
    actual = {
        name
        for name in dir(value)
        if not name.startswith("_") and not callable(getattr(value, name))
    }
    assert actual == expected, value


def _serialize_contract_value(value: object) -> object:
    """Serialize the documented public runtime variants for JSON contracts."""
    if isinstance(value, CanonicalDirective):
        _assert_public_data_attributes(value, {"text", "kind", "operands"})
        return {
            "text": value.text,
            "kind": value.kind.value,
            "operands": dict(value.operands),
        }
    if isinstance(value, DraftResult):
        _assert_public_data_attributes(value, {"source", "result"})
        return {"source": value.source, "result": _serialize_contract_value(value.result)}
    if isinstance(value, NoDirective | UnknownDirective):
        _assert_public_data_attributes(value, {"reason"})
        return {"reason": value.reason}
    if isinstance(value, dict):
        return {key: _serialize_contract_value(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_serialize_contract_value(item) for item in value]
    return value


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
        if expected_param.get("has_default") and "default" in expected_param:
            assert actual.default == expected_param["default"], label


def _assert_signature_schema(signature_spec: dict[str, object], label: str) -> None:
    _assert_exact_keys(signature_spec, {"is_async", "params"}, label)
    assert isinstance(signature_spec["is_async"], bool), label
    params = signature_spec["params"]
    assert isinstance(params, list), label
    for index, parameter in enumerate(params):
        assert isinstance(parameter, dict), f"{label}.params[{index}]"
        _assert_exact_keys(
            parameter,
            {"name", "kind", "has_default"} | ({"default"} if "default" in parameter else set()),
            f"{label}.params[{index}]",
        )
        assert isinstance(parameter["name"], str), f"{label}.params[{index}]"
        assert parameter["kind"] in {
            "POSITIONAL_ONLY",
            "POSITIONAL_OR_KEYWORD",
            "VAR_POSITIONAL",
            "KEYWORD_ONLY",
            "VAR_KEYWORD",
        }, f"{label}.params[{index}]"
        assert isinstance(parameter["has_default"], bool), f"{label}.params[{index}]"
        if "default" in parameter:
            assert parameter["has_default"], f"{label}.params[{index}]"


def _assert_forbidden_names_schema(names: object, label: str) -> None:
    assert isinstance(names, list), label
    assert all(isinstance(name, str) and name for name in names), label
    assert len(names) == len(set(names)), label


def _assert_constructor_probe_schema(probe: dict[str, object], label: str) -> None:
    _assert_exact_keys(probe, {"case", "args", "kwargs", "expect"}, label)
    assert probe["case"] in {
        "missing_required",
        "extra_argument",
        "wrong_type",
        "invalid_enum",
        "semantic_invalid",
        "valid",
    }, label
    assert isinstance(probe["args"], list), label
    assert isinstance(probe["kwargs"], dict), label
    expect = probe["expect"]
    assert isinstance(expect, dict), label
    if set(expect) == {"success"}:
        assert isinstance(expect["success"], bool), label
    else:
        _assert_exact_keys(expect, {"exception"}, label)
        assert isinstance(expect["exception"], str), label


def _assert_constructor_spec_schema(spec: dict[str, object], label: str) -> None:
    _assert_exact_keys(spec, {"signature", "probes"}, label)
    _assert_signature_schema(spec["signature"], f"{label}.signature")
    assert isinstance(spec["probes"], list) and spec["probes"], label
    for index, probe in enumerate(spec["probes"]):
        assert isinstance(probe, dict), f"{label}.probes[{index}]"
        _assert_constructor_probe_schema(probe, f"{label}.probes[{index}]")


def _assert_converter_prompt_behavior_probe_schema(probe: dict[str, object], label: str) -> None:
    _assert_exact_keys(
        probe,
        {"kind", "expect_substrings"} | ({"reject_substrings"} & set(probe.keys())),
        label,
    )
    assert probe["kind"] == "get_converter_prompt"
    expect_substrings = probe["expect_substrings"]
    assert isinstance(expect_substrings, list)
    assert all(isinstance(item, str) for item in expect_substrings)
    reject_substrings = probe.get("reject_substrings", [])
    assert isinstance(reject_substrings, list)
    assert all(isinstance(item, str) for item in reject_substrings)


def _assert_directive_drafter_behavior_probe_schema(probe: dict[str, object], label: str) -> None:
    _assert_exact_keys(probe, {"kind", "user_input", "expect_result"}, label)
    assert probe["kind"] == "directive_drafter_draft", label
    assert isinstance(probe["user_input"], str), label
    assert isinstance(probe["expect_result"], dict), label
    _assert_shape_schema(probe["expect_result"], f"{label}.expect_result")


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
            if probe.get("kind") == "get_converter_prompt":
                _assert_converter_prompt_behavior_probe_schema(
                    probe, f"{label}.behavior_probes[{index}]"
                )
                continue
            raise AssertionError(f"Unsupported behavior probe for {label}: {probe!r}")


def _assert_class_spec_schema(spec: dict[str, object], label: str) -> None:
    _assert_exact_keys(
        spec,
        {"kind"}
        | (
            {"constructor", "forbidden_members", "public_members", "behavior_probes"}
            & set(spec.keys())
        ),
        label,
    )
    if "forbidden_members" in spec:
        _assert_forbidden_names_schema(spec["forbidden_members"], f"{label}.forbidden_members")
    if "constructor" in spec:
        _assert_constructor_spec_schema(spec["constructor"], f"{label}.constructor")
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


def _assert_converter_prompt_behavior_probe(exported: object, probe: dict[str, object]) -> None:
    result = exported()
    for substring in probe["expect_substrings"]:
        assert substring in result
    for substring in probe.get("reject_substrings", []):
        assert substring not in result


def _assert_directive_drafter_behavior_probe(exported: object, probe: dict[str, object]) -> None:
    drafter = exported()
    result = drafter.draft_directive(probe["user_input"])
    _assert_shape(_serialize_contract_value(result), probe["expect_result"])


def _resolve_constructor_value(value: object) -> object:
    if isinstance(value, list):
        return [_resolve_constructor_value(item) for item in value]
    if isinstance(value, dict):
        if set(value) == {"enum"}:
            module_name, enum_name, member_name = value["enum"].rsplit(".", 2)
            enum_type = getattr(import_module(module_name), enum_name)
            return getattr(enum_type, member_name)
        return {key: _resolve_constructor_value(nested) for key, nested in value.items()}
    return value


def _assert_constructor_contract(exported: object, spec: dict[str, object], label: str) -> None:
    _assert_signature_matches(exported, spec["signature"], f"{label}.__init__")
    for probe in spec["probes"]:
        args = _resolve_constructor_value(probe["args"])
        kwargs = _resolve_constructor_value(probe["kwargs"])
        expect = probe["expect"]
        try:
            exported(*args, **kwargs)
        except Exception as error:
            assert set(expect) == {"exception"}, (label, probe)
            assert type(error).__name__ == expect["exception"], (label, probe, error)
        else:
            assert expect == {"success": True}, (label, probe)


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
            _assert_shape(_serialize_contract_value(result), return_shape)

    for probe in spec.get("behavior_probes", []):
        if name == "get_converter_prompt":
            _assert_converter_prompt_behavior_probe(exported, probe)
            continue
        raise AssertionError(f"Unsupported behavior probe for {name}: {probe!r}")


def _assert_class_contract(name: str, exported: object, spec: dict[str, object]) -> None:
    _assert_export_kind(name, exported, "class")

    for member_name in spec.get("forbidden_members", []):
        assert not hasattr(exported, member_name), f"{name}.{member_name}"

    if "constructor" in spec:
        _assert_constructor_contract(exported, spec["constructor"], name)

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
        _assert_forbidden_names_schema(contract["forbidden_exports"], f"{label}.forbidden_exports")
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


def test_required_public_api_contract_fixtures_are_present() -> None:
    actual = {path.name for path in _contract_paths()}
    assert actual >= _REQUIRED_CONTRACT_FILES


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
        module = import_module(contract["module"])
        for name in contract["members"]:
            assert hasattr(module, name), f"{path.name}:{name}"
            if module is package:
                assert name in package.__all__, f"{path.name}:{name}"


def test_public_api_contracts_validate_kinds_signatures_and_shapes(
    tmp_path: Path,
) -> None:
    for path in _contract_paths():
        contract = _load_contract(path)
        module = import_module(contract["module"])
        members = (
            contract["exports"]["members"]
            if contract["kind"] == "api-surface-contract"
            else contract["members"]
        )
        for name, spec in members.items():
            exported = getattr(module, name)
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
        "DraftResultType",
        "DirectiveDrafter",
        "NoDirective",
        "UnknownDirective",
        "parse_preprocessor_output",
        "preprocess_heuristic",
        "get_converter_prompt",
        "validate_preprocessor_output",
    }


def test_typing_only_names_are_not_importable_from_package_root() -> None:
    imported = import_module("context_compiler_directive_drafter")
    for name in ["DraftOutcome", "PreprocessResult"]:
        assert name not in imported.__dict__, name


def test_forbidden_class_members_are_rejected_by_the_harness() -> None:
    class LegacyResult:
        outcome = "directive"

    with pytest.raises(AssertionError):
        _assert_class_contract(
            "LegacyResult",
            LegacyResult,
            {"kind": "class", "forbidden_members": ["outcome"]},
        )


def test_directive_drafter_constructor_supports_optional_fallback() -> None:
    signature = inspect.signature(package.DirectiveDrafter)
    parameters = list(signature.parameters.values())

    assert len(parameters) == 4
    assert parameters[0].name == "fallback"
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[0].default is None
    assert parameters[1].name == "fallback_source"
    assert parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[1].default == "fallback"
    assert parameters[2].name == "async_fallback"
    assert parameters[2].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[2].default is None
    assert parameters[3].name == "async_fallback_source"
    assert parameters[3].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[3].default == "fallback"
