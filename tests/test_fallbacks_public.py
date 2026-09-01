from context_compiler_directive_drafter import _prompts
from context_compiler_directive_drafter.drafter import InvalidFallbackResponseError
from context_compiler_directive_drafter.fallbacks import (
    NO_DIRECTIVE,
    get_converter_prompt,
    get_structured_converter_prompt,
    get_structured_output_schema,
)


def test_public_fallback_prompts_reuse_package_prompt_sources() -> None:
    assert get_converter_prompt() == _prompts._get_converter_prompt()
    assert get_structured_converter_prompt() == _prompts._get_structured_converter_prompt()


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
