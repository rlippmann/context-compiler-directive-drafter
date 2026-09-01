"""OpenAI-compatible fallback factory."""

from context_compiler_directive_drafter.openai_fallback import (
    create_async_openai_fallback,
    create_openai_fallback,
)

__all__ = ["create_async_openai_fallback", "create_openai_fallback"]
