"""Canonical directive refinement boundary.

This module intentionally operates only on canonical directive data and the
public engine read interface. It does not interpret natural language, mutate
authoritative state, or replace core validation/execution.
"""

from context_compiler import Engine
from context_compiler.grammar import (
    CanonicalDirective,
    DirectiveKind,
    decompose_directive,
    render_directive,
)


def refine_directive(directive: CanonicalDirective, engine: Engine) -> CanonicalDirective:
    """Return a canonical directive after applying deterministic refinement.

    Args:
        directive: Already-canonical directive data to refine, if needed.
        engine: Read-only compiler context consulted for deterministic
            premise/policy refinement decisions. This function does not apply
            directives or mutate authoritative state through the engine.

    Returns:
        A canonical directive proposal that may be rewritten to match current
        premise context while remaining non-authoritative.
    """

    if directive.kind is DirectiveKind.SET_PREMISE and engine.premise is not None:
        refined = render_directive(
            DirectiveKind.CHANGE_PREMISE,
            value=directive.operands["value"],
        )
        refined_directive = decompose_directive(refined)
        assert refined_directive is not None
        return refined_directive

    if directive.kind is DirectiveKind.CHANGE_PREMISE and engine.premise is None:
        refined = render_directive(
            DirectiveKind.SET_PREMISE,
            value=directive.operands["value"],
        )
        refined_directive = decompose_directive(refined)
        assert refined_directive is not None
        return refined_directive

    _ = engine.policies
    return directive
