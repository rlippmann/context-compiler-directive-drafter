import hashlib
import json
from enum import Enum
from pathlib import Path

import pytest
from context_compiler.grammar import DirectiveKind

from context_compiler_directive_drafter.drafter import InvalidFallbackResponseError
from context_compiler_directive_drafter.fallbacks import (
    NO_DIRECTIVE,
    AsyncDraftFallback,
    DraftFallback,
    FallbackProfile,
    get_fallback_profile,
    get_structured_output_schema,
    parse_structured_response,
)
from context_compiler_directive_drafter.fallbacks import _prompts as prompts
from context_compiler_directive_drafter.fallbacks.openai import create_openai_fallback


def test_public_fallback_spec_selects_provider_neutral_material() -> None:
    free_text = get_fallback_profile()
    structured = get_fallback_profile(structured_output=True)

    assert isinstance(free_text, FallbackProfile)
    assert free_text.mode == "free_text"
    assert free_text.response_schema is None
    assert structured.mode == "structured"
    assert structured.response_schema is not None
    assert structured.system_prompt != free_text.system_prompt
    assert prompts._get_converter_prompt() == free_text.system_prompt
    assert prompts._get_structured_converter_prompt() == structured.system_prompt


def test_public_fallback_spec_can_restrict_directive_kinds() -> None:
    spec = get_fallback_profile(allowed_directive_kinds={DirectiveKind.USE_ITEM})

    assert "`use <item>`" in spec.system_prompt
    assert "`prohibit <item>`" not in spec.system_prompt
    assert "Only these directive kinds may be proposed: `use_item`." in spec.system_prompt
    assert "cannot be represented by exactly one of these kinds, abstain" in spec.system_prompt


def test_public_fallback_profile_rejects_unknown_directive_kind() -> None:
    class UnknownKind(Enum):
        UNKNOWN = "unknown"

    with pytest.raises(ValueError, match="Unknown directive kinds"):
        get_fallback_profile(allowed_directive_kinds={UnknownKind.UNKNOWN})  # type: ignore[arg-type]


def test_contractual_profiles_preserve_exact_rendered_artifacts() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "contracts" / "fallback-integration-v1.json"
    contract = json.loads(fixture_path.read_text(encoding="utf-8"))
    kinds = {kind.value: kind for kind in DirectiveKind}

    for expected in contract["profiles"]:
        allowed = expected["allowed_directive_kinds"]
        profile = get_fallback_profile(
            structured_output=expected["structured_output"],
            allowed_directive_kinds=None if allowed is None else {kinds[kind] for kind in allowed},
        )

        assert profile.mode == expected["mode"]
        assert (
            hashlib.sha256(profile.system_prompt.encode()).hexdigest()
            == expected["system_prompt_sha256"]
        )
        assert profile.response_schema == expected["response_schema"]
        assert profile.abstention_sentinel == expected["abstention_sentinel"]


def test_public_callback_contract_preserves_original_input_and_none() -> None:
    received: list[str] = []

    def fallback(user_input: str) -> str | None:
        received.append(user_input)
        return None

    sync_contract: DraftFallback = fallback
    assert sync_contract("the original request") is None
    assert received == ["the original request"]

    async def async_fallback(user_input: str) -> str | None:
        received.append(user_input)
        return None

    async_contract: AsyncDraftFallback = async_fallback
    assert async_contract is async_fallback


def test_public_fallback_schema_is_structural_and_defensive() -> None:
    schema = get_structured_output_schema()

    assert schema == {
        "type": "object",
        "properties": {
            "classification": {"type": "string", "enum": ["directive", "rejected"]},
            "output": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
        "required": ["classification", "output"],
        "additionalProperties": False,
    }

    schema["properties"]["classification"]["enum"].append("invalid")
    assert "invalid" not in get_structured_output_schema()["properties"]["classification"]["enum"]


def test_public_fallback_sentinel_and_invalid_response_error_are_available() -> None:
    assert NO_DIRECTIVE == "<NO_DIRECTIVE>"
    assert issubclass(InvalidFallbackResponseError, RuntimeError)


def test_structured_response_parser_distinguishes_rejection_from_invalid_output() -> None:
    assert parse_structured_response('{"classification":"rejected","output":null}') is None

    with pytest.raises(InvalidFallbackResponseError):
        parse_structured_response('{"classification":"directive","output":null}')


def test_openai_factory_is_available_under_fallback_namespace() -> None:
    assert create_openai_fallback.__name__ == "create_openai_fallback"


def test_fallback_value_records_use_slots() -> None:
    from context_compiler_directive_drafter.drafter import (
        DirectiveDrafter,
        DraftResult,
        RejectedDirective,
        UnknownDirective,
    )

    assert DirectiveDrafter.__slots__ == (
        "_fallback",
        "_fallback_source",
        "_async_fallback",
        "_async_fallback_source",
    )
    assert hasattr(DraftResult, "__slots__")
    assert hasattr(RejectedDirective, "__slots__")
    assert hasattr(UnknownDirective, "__slots__")
