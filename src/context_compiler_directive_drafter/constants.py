"""Shared protocol constants for directive-drafting paths."""

from typing import Final, Literal

PREPROCESSOR_NO_DIRECTIVE_SENTINEL: Final = "<NO_DIRECTIVE>"

DRAFT_OUTCOME_DIRECTIVE: Final = "directive"
DRAFT_OUTCOME_REJECTED: Final = "rejected"
DRAFT_OUTCOME_UNKNOWN: Final = "unknown"
DraftOutcome = Literal["directive", "rejected", "unknown"]
OutputClassification = Literal["directive", "rejected"]

REASON_ORDINARY_NON_DIRECTIVE: Final = "ordinary_non_directive"
REASON_QUESTION_FORM: Final = "question_form"
REASON_QUOTED_REPORTED: Final = "quoted_reported"
REASON_INCOMPLETE_DIRECTIVE: Final = "incomplete_directive"
REASON_COMPOUND_DIRECTIVE: Final = "compound_directive"
REASON_MULTI_SENTENCE: Final = "multi_sentence"
REASON_MALFORMED_DIRECTIVE: Final = "malformed_directive"
REASON_UNSUPPORTED_INPUT: Final = "unsupported_input"
REASON_INVALID_FALLBACK_OUTPUT: Final = "invalid_fallback_output"
REASON_FALLBACK_NO_CANDIDATE: Final = "fallback_no_candidate"
REASON_SEMANTIC_UNCERTAINTY: Final = "semantic_uncertainty"

RejectedReason = Literal[
    "ordinary_non_directive",
    "question_form",
    "quoted_reported",
    "incomplete_directive",
    "compound_directive",
    "multi_sentence",
    "malformed_directive",
    "unsupported_input",
    "invalid_fallback_output",
    "fallback_no_candidate",
]
UnknownReason = Literal["semantic_uncertainty"]
