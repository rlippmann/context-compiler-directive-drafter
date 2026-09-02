"""Provider-neutral fallback acquisition material."""

from collections.abc import Collection
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from context_compiler.grammar import DirectiveKind, get_directive_metadata

from ..constants import NO_DIRECTIVE
from . import _prompts

_FallbackMode = Literal["free_text", "structured"]


@dataclass(frozen=True, slots=True)
class FallbackProfile:
    """Package-owned material an adapter needs for one fallback transport mode.

    The fields are provider-neutral acquisition material. Provider adapters
    translate this profile into transport-specific request options and parse
    responses separately.
    """

    system_prompt: str
    mode: _FallbackMode
    response_schema: dict[str, Any] | None
    abstention_sentinel: str | None


_STRUCTURED_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "classification": {"type": "string", "enum": ["directive", "rejected"]},
        "output": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["classification", "output"],
    "additionalProperties": False,
}


def get_fallback_profile(
    *,
    structured_output: bool = False,
    allowed_directive_kinds: Collection[DirectiveKind] | None = None,
) -> FallbackProfile:
    """Select package-owned fallback material for an adapter.

    Args:
        structured_output: Select the structured response envelope instead of
            the free-text candidate contract.
        allowed_directive_kinds: Optional Core directive kinds the fallback
            may propose. This narrows the package-owned prompt inventory; it
            does not replace Core validation.

    Returns:
        A provider-neutral profile containing the system prompt, mode,
        structured schema when applicable, and the free-text abstention
        sentinel when applicable.

    Raises:
        ValueError: If ``allowed_directive_kinds`` contains an unknown Core
            directive kind.
    """

    allowed = None if allowed_directive_kinds is None else frozenset(allowed_directive_kinds)
    if allowed is not None:
        known = {metadata.kind for metadata in get_directive_metadata()}
        unknown = allowed - known
        if unknown:
            raise ValueError(f"Unknown directive kinds: {sorted(kind.value for kind in unknown)!r}")
    mode: _FallbackMode = "structured" if structured_output else "free_text"
    prompt = (
        _prompts._get_structured_converter_prompt()
        if structured_output and allowed is None
        else _prompts._get_converter_prompt()
        if not structured_output and allowed is None
        else _prompts._render_prompt(mode, allowed)
    )
    return FallbackProfile(
        system_prompt=prompt,
        mode=mode,
        response_schema=deepcopy(_STRUCTURED_OUTPUT_SCHEMA) if structured_output else None,
        abstention_sentinel=None if structured_output else NO_DIRECTIVE,
    )
