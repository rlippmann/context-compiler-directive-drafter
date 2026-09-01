"""Public fallback-integration helpers.

These helpers let a host implement a native fallback callback without taking
ownership of directive grammar or acquisition semantics.
"""

from copy import deepcopy
from typing import Any

from context_compiler_directive_drafter._prompts import (
    get_converter_prompt,
    get_structured_converter_prompt,
)
from context_compiler_directive_drafter.constants import NO_DIRECTIVE
from context_compiler_directive_drafter.drafter import InvalidFallbackResponseError


def get_structured_output_schema() -> dict[str, Any]:
    """Return the structural JSON Schema for the structured fallback envelope."""

    return deepcopy(_STRUCTURED_OUTPUT_SCHEMA)


_STRUCTURED_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "classification": {"type": "string", "enum": ["directive", "rejected"]},
        "output": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["classification", "output"],
    "additionalProperties": False,
}


__all__ = [
    "InvalidFallbackResponseError",
    "NO_DIRECTIVE",
    "get_converter_prompt",
    "get_structured_converter_prompt",
    "get_structured_output_schema",
]
