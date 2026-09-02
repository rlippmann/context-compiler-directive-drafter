"""Private shared types for fallback integration modules.

The public callback aliases live here so the drafter and fallback package can
share them without importing the public fallback facade during initialization.
``fallbacks.__init__`` is their only public export.
"""

from collections.abc import Awaitable, Callable

DraftFallback = Callable[[str], str | None]
AsyncDraftFallback = Callable[[str], Awaitable[str | None]]


class InvalidFallbackResponseError(RuntimeError):
    """Signal that a provider returned a malformed fallback response."""

    __slots__ = ()
