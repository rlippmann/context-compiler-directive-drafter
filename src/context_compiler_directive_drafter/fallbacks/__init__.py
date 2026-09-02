"""Public fallback-integration surface.

These helpers let a host implement a native fallback callback without taking
ownership of directive grammar or acquisition semantics.

Implementation modules such as ``_types`` and ``_prompts`` are intentionally
private; this module is the conformance-facing namespace for fallback APIs.
"""

import json

# Re-export the callback contracts and profile from this namespace so adapters
# do not depend on their implementation modules.
from context_compiler_directive_drafter.fallbacks._types import (
    AsyncDraftFallback,
    DraftFallback,
    InvalidFallbackResponseError,
)
from context_compiler_directive_drafter.fallbacks.profile import (
    FallbackProfile,
    get_fallback_profile,
)


def parse_structured_response(content: str) -> str | None:
    """Parse a provider response into candidate text or fallback abstention.

    Args:
        content: JSON text using the package-owned structured response envelope.

    Returns:
        The candidate directive text, or ``None`` when the provider rejected
        the input.

    Raises:
        InvalidFallbackResponseError: If the response is malformed or its
            classification and output do not agree.
    """

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


__all__ = [
    "FallbackProfile",
    "DraftFallback",
    "AsyncDraftFallback",
    "get_fallback_profile",
    "InvalidFallbackResponseError",
    "parse_structured_response",
]
