"""Canonical directive refinement boundary.

This module intentionally operates only on canonical directive data and the
public engine read interface. It does not interpret natural language, mutate
authoritative state, or replace core validation/execution.
"""

from context_compiler import Engine
from context_compiler.grammar import CanonicalDirective


def refine_directive(directive: CanonicalDirective, engine: Engine) -> CanonicalDirective:
    """Return a canonical directive after applying deterministic refinement.

    The initial implementation is intentionally a no-op placeholder. It accepts
    an already-valid canonical directive representation plus an engine exposing
    read-only authoritative state and returns the directive unchanged.
    """

    _ = engine.premise, engine.policies
    return directive
