"""Public fallback-integration helpers.

These helpers let a host implement a native fallback callback without taking
ownership of directive grammar or acquisition semantics.
"""

import json
from copy import deepcopy
from typing import Any

from context_compiler_directive_drafter.constants import NO_DIRECTIVE
from context_compiler_directive_drafter.drafter import InvalidFallbackResponseError
from context_compiler_directive_drafter.fallbacks.prompts import (
    get_converter_prompt,
    get_structured_converter_prompt,
)


def get_structured_output_schema() -> dict[str, Any]:
    """Return the structural JSON Schema for the structured fallback envelope."""

    return deepcopy(_STRUCTURED_OUTPUT_SCHEMA)


def parse_structured_response(content: str) -> str | None:
    """Parse a structured fallback envelope into candidate text or abstention."""

    try:
        envelope = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise InvalidFallbackResponseError("structured fallback response is not JSON") from exc
    if not isinstance(envelope, dict) or set(envelope) != {"classification", "output"}:
        raise InvalidFallbackResponseError("structured fallback response has an invalid envelope")
    classification = envelope["classification"]
    output = envelope["output"]
    if classification == "directive" and isinstance(output, str):
        return output
    if classification == "rejected" and output is None:
        return None
    raise InvalidFallbackResponseError("structured fallback response is inconsistent")


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
    "parse_structured_response",
]
