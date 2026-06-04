"""Public package surface for context-compiler-directive-drafter."""

from context_compiler_directive_drafter.constants import (
    PREPROCESS_OUTCOME_DIRECTIVE,
    PREPROCESS_OUTCOME_NO_DIRECTIVE,
    PREPROCESS_OUTCOME_UNKNOWN,
    PREPROCESSOR_NO_DIRECTIVE_SENTINEL,
    PROMPT_TOKEN_NULL_OR_VALUE,
    PROMPT_TOKEN_POLICY_SET,
    PreprocessOutcome,
)
from context_compiler_directive_drafter.drafter import DraftResult, draft_directive
from context_compiler_directive_drafter.heuristic_preprocessor import (
    PreprocessResult,
    preprocess_heuristic,
)
from context_compiler_directive_drafter.output_validation import (
    parse_preprocessor_output,
    validate_preprocessor_output,
)
from context_compiler_directive_drafter.prompt_utils import render_prompt

__all__ = [
    "DraftResult",
    "PROMPT_TOKEN_NULL_OR_VALUE",
    "PROMPT_TOKEN_POLICY_SET",
    "PREPROCESSOR_NO_DIRECTIVE_SENTINEL",
    "PREPROCESS_OUTCOME_DIRECTIVE",
    "PREPROCESS_OUTCOME_NO_DIRECTIVE",
    "PREPROCESS_OUTCOME_UNKNOWN",
    "PreprocessOutcome",
    "PreprocessResult",
    "draft_directive",
    "parse_preprocessor_output",
    "preprocess_heuristic",
    "render_prompt",
    "validate_preprocessor_output",
]
