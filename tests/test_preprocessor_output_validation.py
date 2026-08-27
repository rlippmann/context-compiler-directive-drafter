from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter.output_validation import classify_drafter_output


def test_core_canonical_validation_accepts_canonical_shapes() -> None:
    assert decompose_directive("clear state") is not None
    assert decompose_directive("set premise concise replies") is not None
    assert decompose_directive("change premise to formal tone") is not None
    assert decompose_directive("use podman instead of docker") is not None


def test_validate_text_accepts_canonical_directive() -> None:
    result = classify_drafter_output("prohibit peanuts")
    assert result == {
        "classification": "directive",
        "output": "prohibit peanuts",
    }


def test_validate_text_rejects_exact_no_directive_sentinel() -> None:
    result = classify_drafter_output("<NO_DIRECTIVE>")
    assert result == {
        "classification": "rejected",
        "output": None,
    }


def test_validate_text_rejects_malformed_or_mixed_output() -> None:
    assert classify_drafter_output("<NO_DIRECTIPLE>") == {
        "classification": "rejected",
        "output": None,
    }
    assert classify_drafter_output("set premise to concise replies") == {
        "classification": "rejected",
        "output": None,
    }
    assert classify_drafter_output("prohibit peanuts and use almonds") == {
        "classification": "rejected",
        "output": None,
    }
    assert classify_drafter_output("clear premise and reset policies") == {
        "classification": "rejected",
        "output": None,
    }
    assert classify_drafter_output("remove policy docker\nuse podman") == {
        "classification": "rejected",
        "output": None,
    }


def test_validate_structured_output_accepts_strict_contract_shape() -> None:
    assert classify_drafter_output(
        {
            "classification": "directive",
            "output": "clear state",
        }
    ) == {
        "classification": "directive",
        "output": "clear state",
    }

    assert classify_drafter_output(
        {
            "classification": "rejected",
            "output": None,
        }
    ) == {
        "classification": "rejected",
        "output": None,
    }

    assert classify_drafter_output(
        {
            "classification": "unknown",
            "output": None,
        }
    ) == {
        "classification": "rejected",
        "output": None,
    }


def test_validate_structured_output_rejects_malformed_shape_or_payload_as_unknown() -> None:
    cases = [
        None,
        123,
        {},
        {"classification": "directive"},
        {"output": "clear state"},
        {"classification": "directive", "output": None},
        {"classification": "directive", "output": ""},
        {"classification": "directive", "output": "set premise to concise replies"},
        {"classification": "rejected", "output": "clear state"},
        {"classification": "unknown", "output": "clear state"},
        {"classification": "unsupported_action", "output": None},
        {"classification": "directive", "output": "clear state\nreset policies"},
        {
            "classification": "directive",
            "output": "set premise deployment target is staging, then use cautious rollout",
        },
        {"classification": "directive", "output": "clear state", "extra": True},
        {"classification": "directive", "output": "use docker", "extra": True},
        {"classification": "directive", "output": "use docker", "extra_field": "use docker"},
        {"classification": "rejected", "output": None, "extra": "hello"},
        {"action": "prohibit", "item": "peanuts"},
    ]
    for raw in cases:
        assert classify_drafter_output(raw) == {
            "classification": "rejected",
            "output": None,
        }


def test_validate_text_parses_and_validates_json_contract() -> None:
    raw = '{"classification":"directive","output":"use docker"}'
    assert classify_drafter_output(raw) == {
        "classification": "directive",
        "output": "use docker",
    }


def test_custom_host_can_validate_then_parse_with_core() -> None:
    validated = classify_drafter_output("  USE docker  ")
    assert validated == {"classification": "directive", "output": "use docker"}

    parsed = decompose_directive(validated["output"])
    assert parsed is not None
    assert parsed.text == "use docker"
