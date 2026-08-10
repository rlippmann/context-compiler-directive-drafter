"""Shared protocol constants for directive-drafting paths."""

from typing import Final, Literal

PREPROCESSOR_NO_DIRECTIVE_SENTINEL: Final = "<NO_DIRECTIVE>"

DRAFT_OUTCOME_DIRECTIVE: Final = "directive"
DRAFT_OUTCOME_NO_DIRECTIVE: Final = "no_directive"
DRAFT_OUTCOME_UNKNOWN: Final = "unknown"
DraftOutcome = Literal["directive", "no_directive", "unknown"]
