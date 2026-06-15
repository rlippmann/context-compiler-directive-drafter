"""Public package surface for context-compiler-directive-drafter."""

from context_compiler_directive_drafter.constants import (
    PREPROCESS_OUTCOME_DIRECTIVE,
    PREPROCESS_OUTCOME_NO_DIRECTIVE,
    PREPROCESS_OUTCOME_UNKNOWN,
    PREPROCESSOR_NO_DIRECTIVE_SENTINEL,
)
from context_compiler_directive_drafter.heuristic_preprocessor import (
    preprocess_heuristic,
)
from context_compiler_directive_drafter.output_validation import (
    parse_preprocessor_output,
    validate_preprocessor_output,
)
from context_compiler_directive_drafter.prompt_utils import render_prompt

__all__ = [
    "PREPROCESSOR_NO_DIRECTIVE_SENTINEL",
    "PREPROCESS_OUTCOME_DIRECTIVE",
    "PREPROCESS_OUTCOME_NO_DIRECTIVE",
    "PREPROCESS_OUTCOME_UNKNOWN",
    "parse_preprocessor_output",
    "preprocess_heuristic",
    "render_prompt",
    "validate_preprocessor_output",
]
