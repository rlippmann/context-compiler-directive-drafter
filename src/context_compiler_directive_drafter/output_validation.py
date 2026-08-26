"""Shared fallback-candidate normalization and validation helpers.

Public API:
- classify_drafter_output

Internal helpers are implementation details and may change.
"""

import json
from typing import TypedDict

from context_compiler.grammar import CanonicalDirective, decompose_directive

from .constants import (
    DRAFT_OUTCOME_DIRECTIVE,
    DRAFT_OUTCOME_NO_DIRECTIVE,
    DRAFT_OUTCOME_UNKNOWN,
    PREPROCESSOR_NO_DIRECTIVE_SENTINEL,
    DraftOutcome,
)

__all__ = ["classify_drafter_output"]


class PreprocessorValidationResult(TypedDict):
    classification: DraftOutcome
    output: str | None


def _parse_canonical_directive(raw_output: str) -> CanonicalDirective | None:
    decomposed = decompose_directive(raw_output.strip())
    if isinstance(decomposed, CanonicalDirective):
        return decomposed
    return None


def _unknown() -> PreprocessorValidationResult:
    return {"classification": DRAFT_OUTCOME_UNKNOWN, "output": None}


def _directive(output: str) -> PreprocessorValidationResult:
    return {"classification": DRAFT_OUTCOME_DIRECTIVE, "output": output}


def _no_directive() -> PreprocessorValidationResult:
    return {"classification": DRAFT_OUTCOME_NO_DIRECTIVE, "output": None}


def _validate_structured_output(raw_output: object) -> PreprocessorValidationResult:
    if not isinstance(raw_output, dict):
        return _unknown()

    if set(raw_output.keys()) != {"classification", "output"}:
        return _unknown()

    classification = raw_output.get("classification")
    output = raw_output.get("output")
    if not isinstance(classification, str):
        return _unknown()

    if classification == DRAFT_OUTCOME_DIRECTIVE:
        if not isinstance(output, str):
            return _unknown()
        parsed = _parse_canonical_directive(output)
        if parsed is None:
            return _unknown()
        return _directive(parsed.text)

    if classification == DRAFT_OUTCOME_NO_DIRECTIVE:
        if output is not None:
            return _unknown()
        return _no_directive()

    if classification == DRAFT_OUTCOME_UNKNOWN:
        if output is not None:
            return _unknown()
        return _unknown()

    return _unknown()


def _validate_text_output(raw_output: str) -> PreprocessorValidationResult:
    stripped = raw_output.strip()
    if not stripped:
        return _unknown()

    if stripped.upper() == PREPROCESSOR_NO_DIRECTIVE_SENTINEL:
        return _no_directive()

    parsed = _parse_canonical_directive(stripped)
    if parsed is not None:
        return _directive(parsed.text)

    if stripped[0] in {"{", "["}:
        try:
            parsed_json = json.loads(stripped)
        except json.JSONDecodeError:
            return _unknown()
        return _validate_structured_output(parsed_json)

    return _unknown()


def classify_drafter_output(raw_output: object) -> PreprocessorValidationResult:
    """Validate raw preprocessor output into a strict classification/output result.

    Contract:
        - directive: output is a canonical directive string
        - no_directive: output is None
        - unknown: output is None

    This function validates structure and canonical directive shape only. It
    does not decide whether a directive is allowed in the current compiler
    context, and it does not apply any directive.
    """
    if isinstance(raw_output, str):
        validated = _validate_text_output(raw_output)
    else:
        validated = _validate_structured_output(raw_output)

    return validated
