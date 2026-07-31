"""Shared protocol constants for directive-drafting paths."""

import re
from typing import Final, Literal

PREPROCESSOR_NO_DIRECTIVE_SENTINEL: Final = "<NO_DIRECTIVE>"

PREPROCESS_OUTCOME_DIRECTIVE: Final = "directive"
PREPROCESS_OUTCOME_NO_DIRECTIVE: Final = "no_directive"
PREPROCESS_OUTCOME_UNKNOWN: Final = "unknown"
PreprocessOutcome = Literal["directive", "no_directive", "unknown"]

PROMPT_TOKEN_NULL_OR_VALUE: Final = "<NULL_OR_VALUE>"
PROMPT_TOKEN_POLICY_SET: Final = "<SET OF CURRENT POLICY ITEMS>"

CANONICAL_DIRECTIVE_STARTS: Final[tuple[str, ...]] = (
    "change premise to",
    "remove policy",
    "clear premise",
    "reset policies",
    "clear state",
    "set premise",
    "prohibit",
    "use",
)
_CANONICAL_DIRECTIVE_START_PATTERN: Final[re.Pattern[str]] = re.compile(
    "|".join(rf"(?<!\S){re.escape(start)}(?=\s|$)" for start in CANONICAL_DIRECTIVE_STARTS)
)


def count_canonical_directive_starts(text: str) -> int:
    """Count canonical directive starts in normalized free text."""
    normalized = re.sub(r"\s+", " ", text.strip()).lower()
    if not normalized:
        return 0
    return len(_CANONICAL_DIRECTIVE_START_PATTERN.findall(normalized))
