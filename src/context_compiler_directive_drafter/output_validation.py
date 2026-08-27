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
    DRAFT_OUTCOME_REJECTED,
    PREPROCESSOR_NO_DIRECTIVE_SENTINEL,
    OutputClassification,
)

__all__ = ["classify_drafter_output"]


class PreprocessorValidationResult(TypedDict):
    classification: OutputClassification
    output: str | None


def _parse_canonical_directive(raw_output: str) -> CanonicalDirective | None:
    decomposed = decompose_directive(raw_output.strip())
    if isinstance(decomposed, CanonicalDirective):
        return decomposed
    return None


def _invalid() -> PreprocessorValidationResult:
    return {"classification": DRAFT_OUTCOME_REJECTED, "output": None}


def _directive(output: str) -> PreprocessorValidationResult:
    return {"classification": DRAFT_OUTCOME_DIRECTIVE, "output": output}


def _rejected() -> PreprocessorValidationResult:
    return {"classification": DRAFT_OUTCOME_REJECTED, "output": None}


def _validate_structured_output(raw_output: object) -> PreprocessorValidationResult:
    if not isinstance(raw_output, dict):
        return _invalid()

    if set(raw_output.keys()) != {"classification", "output"}:
        return _invalid()

    classification = raw_output.get("classification")
    output = raw_output.get("output")
    if not isinstance(classification, str):
        return _invalid()

    if classification == DRAFT_OUTCOME_DIRECTIVE:
        if not isinstance(output, str):
            return _invalid()
        parsed = _parse_canonical_directive(output)
        if parsed is None:
            return _invalid()
        return _directive(parsed.text)

    if classification == DRAFT_OUTCOME_REJECTED:
        if output is not None:
            return _invalid()
        return _rejected()

    return _invalid()


def _validate_text_output(raw_output: str) -> PreprocessorValidationResult:
    stripped = raw_output.strip()
    if not stripped:
        return _invalid()

    if stripped.upper() == PREPROCESSOR_NO_DIRECTIVE_SENTINEL:
        return _rejected()

    parsed = _parse_canonical_directive(stripped)
    if parsed is not None:
        return _directive(parsed.text)

    if stripped[0] in {"{", "["}:
        try:
            parsed_json = json.loads(stripped)
        except json.JSONDecodeError:
            return _invalid()
        return _validate_structured_output(parsed_json)

    return _invalid()


def classify_drafter_output(raw_output: object) -> PreprocessorValidationResult:
    """Validate raw preprocessor output into a strict classification/output result.

    Contract:
        - directive: output is a canonical directive string
        - rejected: output is None

    This function validates provider output structure and canonical directive
    shape only. It
    does not decide whether a directive is allowed in the current compiler
    context, and it does not apply any directive.
    """
    if isinstance(raw_output, str):
        validated = _validate_text_output(raw_output)
    else:
        validated = _validate_structured_output(raw_output)

    return validated
