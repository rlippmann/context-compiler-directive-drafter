"""Shared protocol constants for directive-drafting paths."""

from typing import Final, Literal

PREPROCESSOR_NO_DIRECTIVE_SENTINEL: Final = "<NO_DIRECTIVE>"

DRAFT_OUTCOME_DIRECTIVE: Final = "directive"
DRAFT_OUTCOME_NO_DIRECTIVE: Final = "no_directive"
DRAFT_OUTCOME_UNKNOWN: Final = "unknown"
DraftOutcome = Literal["directive", "no_directive", "unknown"]

PROMPT_TOKEN_NULL_OR_VALUE: Final = "<NULL_OR_VALUE>"
PROMPT_TOKEN_POLICY_SET: Final = "<SET OF CURRENT POLICY ITEMS>"
