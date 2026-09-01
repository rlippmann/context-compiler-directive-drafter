import pytest

from context_compiler_directive_drafter.drafter import InvalidFallbackResponseError
from context_compiler_directive_drafter.fallbacks import (
    NO_DIRECTIVE,
    get_converter_prompt,
    get_structured_converter_prompt,
    get_structured_output_schema,
    parse_structured_response,
    prompts,
)
from context_compiler_directive_drafter.fallbacks.openai import create_openai_fallback


def test_public_fallback_prompts_reuse_package_prompt_sources() -> None:
    assert get_converter_prompt is prompts.get_converter_prompt
    assert get_structured_converter_prompt is prompts.get_structured_converter_prompt


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
