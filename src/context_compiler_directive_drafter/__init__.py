"""Public package surface for context-compiler-directive-drafter.

The root surface contains the portable drafting and result APIs. This Python
package also re-exports its OpenAI-compatible convenience factories; provider
specific integrations remain outside the portable contract.
"""

from context_compiler_directive_drafter.constants import (
    REASON_INCOMPLETE,
    REASON_INVALID_CANDIDATE,
    REASON_MULTIPLE_DIRECTIVES,
    REASON_NON_DIRECTIVE,
    RejectedReason,
)
from context_compiler_directive_drafter.drafter import (
    DirectiveDrafter,
    DraftResult,
    RejectedDirective,
    UnknownDirective,
)
from context_compiler_directive_drafter.fallbacks.openai import (
    create_async_openai_fallback,
    create_openai_fallback,
)

__all__ = [
    "REASON_NON_DIRECTIVE",
    "REASON_INCOMPLETE",
    "REASON_MULTIPLE_DIRECTIVES",
    "REASON_INVALID_CANDIDATE",
    "DraftResult",
    "DirectiveDrafter",
    "RejectedDirective",
    "RejectedReason",
    "UnknownDirective",
    "create_openai_fallback",
    "create_async_openai_fallback",
]
