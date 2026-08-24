"""Host-layer heuristic directive drafter.

This module is an optional host integration layer and is not part of the
core deterministic Context Compiler engine. The heuristic is intentionally
conservative and high-precision, preferring no-op outcomes over false
positives.
"""

import re
from typing import Literal, TypedDict

from context_compiler.grammar import (
    CanonicalDirective,
    DirectiveKind,
    decompose_directive,
    get_directive_metadata,
)

from .constants import (
    DRAFT_OUTCOME_DIRECTIVE,
    DRAFT_OUTCOME_NO_DIRECTIVE,
    DRAFT_OUTCOME_UNKNOWN,
)


class DirectivePreprocessResult(TypedDict):
    outcome: Literal["directive"]
    directive: CanonicalDirective


class NonDirectivePreprocessResult(TypedDict):
    outcome: Literal["no_directive", "unknown"]
    directive: None
    reason: str


PreprocessResult = DirectivePreprocessResult | NonDirectivePreprocessResult


_REPORTING_BRACKET_MARKERS = (
    "in my notes",
    "notes:",
    "i wrote down",
)

_LIST_MARKER_PATTERN = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+\S")
_META_PREFIX_PATTERN = re.compile(
    r"^\s*(?:example:|for example\b|the command is\b|(?:i|he|she|they) said\b)"
)
_PUNCTUATION_TRIM_PATTERN = re.compile(r"[.!]+\s*$")
_QUOTED_REPORTING_PATTERN = re.compile(
    r"^\s*(?:the\s+(?:doc|docs?|documentation)|\w+)\s+"
    r"(?:literally\s+)?(?:say|says?|said|wrote|quoted)\s*:\s*"
    r'["\'`].+["\'`][.!]?\s*$',
    re.IGNORECASE,
)
_SET_PREMISE_TO_PATTERN = re.compile(r"^set premise to (?P<payload>\S(?:.*\S)?)$")
_CHANGE_PREMISE_MISSING_TO_PATTERN = re.compile(
    r"^change premise (?!to(?:\s|$))(?P<payload>\S(?:.*\S)?)$"
)
_PLEASE_PREFIX_PATTERN = re.compile(r"^please (?P<directive>\S(?:.*\S)?)$")
_ALLOW_ALIAS_PATTERN = re.compile(r"^allow (?P<item>\S(?:.*\S)?)$")
_PROHIBIT_ALIAS_PATTERN = re.compile(r"^(?:do not|don't) use (?P<item>\S(?:.*\S)?)$")
_REPLACE_MISSING_OF_PATTERN = re.compile(
    r"^use (?P<new_item>\S(?:.*\S)?) instead (?!of(?:\s|$))(?P<old_item>\S(?:.*\S)?)$"
)
_REPLACE_SPLIT_OF_PATTERN = re.compile(
    r"^use (?P<new_item>\S(?:.*\S)?) in stead of (?P<old_item>\S(?:.*\S)?)$"
)
_UNSUPPORTED_ALIAS_PATTERNS = (
    re.compile(r"^allow\s+\S(?:.*\S)?$"),
    re.compile(r"^stop\s+using\s+\S(?:.*\S)?$"),
    re.compile(r"^set\s+policy\s+\S(?:.*\S)?\s+prohibit$"),
    re.compile(r"^use\s+instead\s+of\s+\S(?:.*\S)?$"),
    re.compile(r"^use\s+\S(?:.*\S)?\s+not\s+\S(?:.*\S)?$"),
    re.compile(r"^wipe\s+policies$"),
)
_UNSUPPORTED_ADMIN_ALIAS_PATTERNS = (
    re.compile(r"^reset policy$"),
    re.compile(r"^remove policies\s+\S(?:.*\S)?$"),
)
_WRAPPER_PAIRS = {
    ('"', '"'),
    ("'", "'"),
    ("`", "`"),
    ("(", ")"),
    ("[", "]"),
}


def _normalized_for_match(message: str) -> str:
    return re.sub(r"\s+", " ", message.strip()).lower()


def _directive_canonical_starts() -> tuple[str, ...]:
    starts = {metadata.canonical_start for metadata in get_directive_metadata()}
    return tuple(sorted(starts, key=len, reverse=True))


def _directive_cues() -> tuple[str, ...]:
    cues = set(_directive_canonical_starts())
    cues.update(
        canonical_start.removesuffix(" to")
        for canonical_start in _directive_canonical_starts()
        if canonical_start.endswith(" to")
    )
    return tuple(sorted(cues, key=len, reverse=True))


def _directive_alternation(phrases: tuple[str, ...]) -> str:
    return "|".join(re.escape(phrase) for phrase in phrases)


def _matches_multi_segment_pattern(message: str) -> bool:
    return bool(
        re.match(
            rf"^\s*(?:{_directive_alternation(_directive_canonical_starts())})\b"
            r".*\b(?:because|then continue|and then continue|and explain)\b",
            message,
        )
    )


def _contains_directive_cue(message: str) -> bool:
    return bool(re.search(rf"\b(?:{_directive_alternation(_directive_cues())})\b", message))


def _contains_reporting_bracket_mention(message: str) -> bool:
    lower = message.lower()
    if "[" not in lower or "]" not in lower:
        return False
    return any(marker in lower for marker in _REPORTING_BRACKET_MARKERS)


def _strip_terminal_punctuation(message: str) -> str:
    return _PUNCTUATION_TRIM_PATTERN.sub("", message).strip()


def _strip_exact_wrapper(message: str) -> str:
    stripped = message.strip()
    if len(stripped) < 2:
        return stripped
    opener = stripped[0]
    closer = stripped[-1]
    if (opener, closer) not in _WRAPPER_PAIRS:
        return stripped
    inner = stripped[1:-1].strip()
    if not inner:
        return stripped
    return inner


def _normalize_candidate(message: str) -> str:
    stripped = message.strip()
    no_punct = _strip_terminal_punctuation(stripped)
    unwrapped = _strip_exact_wrapper(no_punct)
    return re.sub(r"\s+", " ", unwrapped).strip().lower()


def _is_quoted_or_backtick_wrapped(message: str) -> bool:
    stripped = message.strip()
    if len(stripped) < 2:
        return False
    return (stripped[0], stripped[-1]) in {('"', '"'), ("'", "'"), ("`", "`")}


def _looks_like_unsafe_replacement_acquisition_case(directive: CanonicalDirective) -> bool:
    if directive.kind is not DirectiveKind.USE_ITEM:
        return False

    item = directive.operands["item"]
    normalized_item = item.lower()
    return " instead " in normalized_item or " in stead of " in normalized_item


def _is_reported_quoted_directive(message: str) -> bool:
    return bool(_QUOTED_REPORTING_PATTERN.match(message))


def _rewrite_bounded_candidate(message: str) -> str:
    """Apply deterministic whole-message rewrites before grammar parsing."""
    current = message

    match = _PLEASE_PREFIX_PATTERN.fullmatch(current)
    if match is not None:
        current = match.group("directive")

    match = _SET_PREMISE_TO_PATTERN.fullmatch(current)
    if match is not None:
        return f"set premise {match.group('payload')}"

    match = _CHANGE_PREMISE_MISSING_TO_PATTERN.fullmatch(current)
    if match is not None:
        return f"change premise to {match.group('payload')}"

    match = _ALLOW_ALIAS_PATTERN.fullmatch(current)
    if match is not None:
        return f"use {match.group('item')}"

    match = _PROHIBIT_ALIAS_PATTERN.fullmatch(current)
    if match is not None:
        return f"prohibit {match.group('item')}"

    match = _REPLACE_MISSING_OF_PATTERN.fullmatch(current)
    if match is not None:
        return f"use {match.group('new_item')} instead of {match.group('old_item')}"

    match = _REPLACE_SPLIT_OF_PATTERN.fullmatch(current)
    if match is not None:
        return f"use {match.group('new_item')} instead of {match.group('old_item')}"

    return current


def _is_unsupported_alias(message: str) -> bool:
    return any(pattern.fullmatch(message) for pattern in _UNSUPPORTED_ALIAS_PATTERNS)


def _is_unsupported_admin_alias(message: str) -> bool:
    return any(pattern.fullmatch(message) for pattern in _UNSUPPORTED_ADMIN_ALIAS_PATTERNS)


def preprocess_heuristic(message: str) -> PreprocessResult:
    """Run the conservative structural heuristic preprocessing pass.

    Args:
        message: Raw user text to evaluate as a possible directive.

    Returns:
        A PreprocessResult with:
        - outcome="directive" and a canonical directive object when matched
        - outcome="no_directive" when the heuristic abstains/rejects
        - outcome="unknown" when unresolved and the host should avoid guessing

    Notes:
        This pass is precision-first and intentionally narrow. It may abstain
        on ambiguous or mixed-intent inputs. The returned directive, when
        present, is still a non-authoritative proposal for later compiler
        review.
    """
    if _LIST_MARKER_PATTERN.match(message):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.list_or_enumeration",
        }

    normalized = _normalized_for_match(message)

    if "?" in message and _contains_directive_cue(normalized):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.question_form",
        }

    if _META_PREFIX_PATTERN.match(normalized):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.meta_or_reporting",
        }

    if _matches_multi_segment_pattern(normalized):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.multi_segment_or_mixed_prose",
        }

    if _contains_reporting_bracket_mention(message):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.quoted_reported_bracket",
        }

    if _is_quoted_or_backtick_wrapped(message):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.quoted_exact",
        }

    if _is_reported_quoted_directive(message):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.quoted_reported",
        }

    normalized_candidate = _rewrite_bounded_candidate(_normalize_candidate(message))

    if _is_unsupported_alias(normalized_candidate):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.near_miss_alias",
        }

    if _is_unsupported_admin_alias(normalized_candidate):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.admin_near_miss_alias",
        }

    decomposed = decompose_directive(normalized_candidate)
    if isinstance(decomposed, CanonicalDirective):
        if _looks_like_unsafe_replacement_acquisition_case(decomposed):
            return {
                "outcome": DRAFT_OUTCOME_UNKNOWN,
                "directive": None,
                "reason": "reject.malformed_replacement_syntax",
            }
        return {
            "outcome": DRAFT_OUTCOME_DIRECTIVE,
            "directive": decomposed,
        }

    if decomposed is not None:
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }

    if _contains_directive_cue(normalized_candidate):
        return {
            "outcome": DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }

    return {
        "outcome": DRAFT_OUTCOME_NO_DIRECTIVE,
        "directive": None,
        "reason": "reject.confident_non_directive",
    }
