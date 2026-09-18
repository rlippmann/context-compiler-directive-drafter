"""Public result constants and private protocol values for directive drafting.

The ``REASON_*`` constants and ``RejectedReason`` alias are stable host-facing
values. Underscored names support Python implementation classification and are
not part of the public API.
"""

from typing import Final, Literal

NO_DIRECTIVE: Final = "<NO_DIRECTIVE>"

# Public rejection reasons are stable host-facing result values. The drafter
# owns acquisition classification; Core remains authoritative for application
# and state transitions.

_DRAFT_OUTCOME_DIRECTIVE: Final = "directive"
_DRAFT_OUTCOME_REJECTED: Final = "rejected"
_DRAFT_OUTCOME_UNKNOWN: Final = "unknown"
_DraftOutcome = Literal["directive", "rejected", "unknown"]
_OutputClassification = Literal["directive", "rejected"]

REASON_NON_DIRECTIVE: Final = "non_directive"
REASON_INCOMPLETE: Final = "incomplete"
REASON_MULTIPLE_DIRECTIVES: Final = "multiple_directives"
REASON_INVALID_CANDIDATE: Final = "invalid_candidate"

_REASON_ORDINARY_NON_DIRECTIVE: Final = "ordinary_non_directive"
_REASON_QUESTION_FORM: Final = "question_form"
_REASON_QUOTED_REPORTED: Final = "quoted_reported"
_REASON_INCOMPLETE_DIRECTIVE: Final = "incomplete_directive"
_REASON_COMPOUND_DIRECTIVE: Final = "compound_directive"
_REASON_MULTI_SENTENCE: Final = "multi_sentence"
_REASON_MALFORMED_DIRECTIVE: Final = "malformed_directive"
_REASON_UNSUPPORTED_INPUT: Final = "unsupported_input"
_REASON_INVALID_FALLBACK_OUTPUT: Final = "invalid_fallback_output"
_REASON_FALLBACK_NO_CANDIDATE: Final = "fallback_no_candidate"
_REASON_SEMANTIC_UNCERTAINTY: Final = "semantic_uncertainty"

RejectedReason = Literal[
    "non_directive",
    "incomplete",
    "multiple_directives",
    "invalid_candidate",
]
UnknownReason = Literal["semantic_uncertainty"]
