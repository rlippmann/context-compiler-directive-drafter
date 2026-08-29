"""Host-layer heuristic directive drafter.

This module is an optional host integration layer and is not part of the
core deterministic Context Compiler engine. It drafts one canonical candidate
from exact input, bounded deterministic rewrites, or clearly non-directive
boundaries; ambiguous interpretation remains fallback-eligible.
"""

import re
from typing import Literal, TypedDict

from context_compiler.grammar import (
    CanonicalDirective,
    decompose_directive,
    get_directive_metadata,
)

from .constants import (
    _DRAFT_OUTCOME_DIRECTIVE,
    _DRAFT_OUTCOME_REJECTED,
    _DRAFT_OUTCOME_UNKNOWN,
    _REASON_COMPOUND_DIRECTIVE,
    _REASON_INCOMPLETE_DIRECTIVE,
    _REASON_MALFORMED_DIRECTIVE,
    _REASON_MULTI_SENTENCE,
    _REASON_ORDINARY_NON_DIRECTIVE,
    _REASON_QUESTION_FORM,
    _REASON_QUOTED_REPORTED,
    _REASON_SEMANTIC_UNCERTAINTY,
    _REASON_UNSUPPORTED_INPUT,
)


class _DirectivePreprocessResult(TypedDict):
    outcome: Literal["directive"]
    directive: CanonicalDirective


class _NonDirectivePreprocessResult(TypedDict):
    outcome: Literal["rejected", "unknown"]
    directive: None
    reason: str


_PreprocessResult = _DirectivePreprocessResult | _NonDirectivePreprocessResult


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
_SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<!\d)[.!?](?!\d)(?:[\"')\]]+)?\s+(?=[A-Za-z])")
_QUOTED_REPORTING_PATTERN = re.compile(
    r"^\s*.+?\s+(?:literally\s+)?(?:say|says?|said|wrote|quoted|told)\b"
    r"(?:\s+\w+)?\s*[:,]?\s*"
    r'["\'`].+["\'`][.!]?\s*$',
    re.IGNORECASE,
)
_INCOMPLETE_PROHIBIT_PATTERN = re.compile(r"^prohibit\s+\S(?:.*\S)?\s+(?:to|with)$")
_SET_PREMISE_TO_PATTERN = re.compile(r"^set premise to (?P<payload>\S(?:.*\S)?)$")
_CHANGE_PREMISE_MISSING_TO_PATTERN = re.compile(
    r"^change premise (?!to(?:\s|$))(?P<payload>\S(?:.*\S)?)$"
)
_PLEASE_PREFIX_PATTERN = re.compile(r"^please (?P<directive>\S(?:.*\S)?)$")
_PREFERENCE_PREFIX_PATTERN = re.compile(r"^i prefer (?P<payload>\S(?:.*\S)?)$")
_ALLOW_ALIAS_PATTERN = re.compile(r"^allow (?P<item>\S(?:.*\S)?)$")
_PROHIBIT_ALIAS_PATTERN = re.compile(r"^(?:do not|don't) use (?P<item>\S(?:.*\S)?)$")
_STOP_USING_ALIAS_PATTERN = re.compile(r"^stop using (?P<item>\S(?:.*\S)?)$")
_TRANSPOSED_PROHIBIT_PATTERN = re.compile(r"^set policy (?P<item>\S(?:.*\S)?) prohibit$")
_DIRECTIVE_REWRITE_CUE_PATTERN = re.compile(
    r"^\s*(?:please|allow|(?:do not|don't) use|stop using|set premise|"
    r"change premise|use)\b"
)
_CONFIDENT_NON_DIRECTIVE_PATTERN = re.compile(
    r"^\s*(?:hi|hello|hey|good (?:morning|afternoon|evening)|thank you|"
    r"thanks(?: for (?:the|your) help(?: today)?| a lot)?)\s*[.!]?\s*$",
    re.IGNORECASE,
)
_REPLACE_MISSING_OF_PATTERN = re.compile(
    r"^use (?P<new_item>\S(?:.*\S)?) instead (?!of(?:\s|$))(?P<old_item>\S(?:.*\S)?)$"
)
_REPLACE_SPLIT_OF_PATTERN = re.compile(
    r"^use (?P<new_item>\S(?:.*\S)?) in stead of (?P<old_item>\S(?:.*\S)?)$"
)
_AMBIGUOUS_ALIAS_PATTERNS = (
    re.compile(r"^use\s+instead\s+of\s+\S(?:.*\S)?$"),
    re.compile(r"^use\s+\S(?:.*\S)?\s+not\s+\S(?:.*\S)?$"),
)
_UNSUPPORTED_ALIAS_PATTERNS = (
    re.compile(r"^wipe\s+policies$"),
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
_MALFORMED_DIRECTIVE_LOOKALIKE_PATTERN = re.compile(r"^\s*[^\s]*[^\x00-\x7f][^\s]*\s+\S(?:.*\S)?$")


def _has_multiple_directive_starts(message: str) -> bool:
    pattern = rf"\b(?:{_directive_alternation(_directive_canonical_starts())})\b"
    return len(re.findall(pattern, message)) > 1


def _is_incomplete_directive(message: str) -> bool:
    if (
        message
        in {
            "use",
            "prohibit",
            "remove policy",
            "change premise",
            "change premise to",
            "set premise",
            "set premise to",
        }
        or message.endswith(" instead of")
        or message.startswith("use instead of ")
    ):
        return True
    return bool(_INCOMPLETE_PROHIBIT_PATTERN.fullmatch(message))


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
            r".*\b(?:"
            r"because|then continue|and then continue|and explain|"
            r"and summarize|and find|and tell)\b",
            message,
        )
    )


def _has_obvious_multi_sentence_boundary(message: str) -> bool:
    """Detect clear sentence boundaries without attempting sentence tokenization."""
    for match in _SENTENCE_BOUNDARY_PATTERN.finditer(message):
        preceding = message[: match.start()].rstrip().lower()
        if preceding.endswith(("e.g", "i.e", "mr", "ms", "dr", "etc")):
            continue

        following = message[match.end() :].strip()
        words = re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)?", following)
        if len(words) >= 2 or re.match(r"^(?:thanks|thank you)(?:[.!?]|$)", following, re.I):
            return True

    return False


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


def _is_reported_quoted_directive(message: str) -> bool:
    return bool(_QUOTED_REPORTING_PATTERN.match(message))


def _rewrite_bounded_candidate(message: str) -> str:
    """Apply deterministic whole-message rewrites before grammar parsing."""
    current = message

    match = _PLEASE_PREFIX_PATTERN.fullmatch(current)
    if match is not None:
        current = match.group("directive")

    match = _PREFERENCE_PREFIX_PATTERN.fullmatch(current)
    if match is not None:
        payload = match.group("payload")
        if re.search(r"\bi prefer\b", payload):
            return current
        current = f"use {payload}"

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

    match = _STOP_USING_ALIAS_PATTERN.fullmatch(current)
    if match is not None:
        return f"prohibit {match.group('item')}"

    match = _TRANSPOSED_PROHIBIT_PATTERN.fullmatch(current)
    if match is not None:
        return f"prohibit {match.group('item')}"

    match = _REPLACE_MISSING_OF_PATTERN.fullmatch(current)
    if match is not None:
        return f"use {match.group('new_item')} instead of {match.group('old_item')}"

    match = _REPLACE_SPLIT_OF_PATTERN.fullmatch(current)
    if match is not None:
        return f"use {match.group('new_item')} instead of {match.group('old_item')}"

    return current


def _is_ambiguous_alias(message: str) -> bool:
    return any(pattern.fullmatch(message) for pattern in _AMBIGUOUS_ALIAS_PATTERNS)


def _is_unsupported_alias(message: str) -> bool:
    return any(pattern.fullmatch(message) for pattern in _UNSUPPORTED_ALIAS_PATTERNS)


def _preprocess_heuristic(message: str) -> _PreprocessResult:
    """Run the bounded structural heuristic preprocessing pass.

    Args:
        message: Raw user text to evaluate as a possible directive.

    Returns:
        An internal preprocessing result with:
        - outcome="directive" and a canonical directive object when matched
        - outcome="rejected" when the input is terminally undraftable
        - outcome="unknown" when unresolved and fallback may interpret it

    Notes:
        This pass accepts exact canonical input and bounded deterministic
        rewrites. It defers ambiguous or mixed-intent inputs. The returned
        directive, when present, is still a non-authoritative proposal; Core
        owns validity, applicability, and execution.
    """
    if _LIST_MARKER_PATTERN.match(message):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_UNSUPPORTED_INPUT,
        }

    normalized = _normalized_for_match(message)

    if "?" in message and (
        _contains_directive_cue(normalized)
        or _DIRECTIVE_REWRITE_CUE_PATTERN.match(normalized)
        or normalized.startswith("i prefer")
    ):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_QUESTION_FORM,
        }

    if "?" in message:
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_ORDINARY_NON_DIRECTIVE,
        }

    if _CONFIDENT_NON_DIRECTIVE_PATTERN.fullmatch(message):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_ORDINARY_NON_DIRECTIVE,
        }

    if _META_PREFIX_PATTERN.match(normalized):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_QUOTED_REPORTED,
        }

    if _matches_multi_segment_pattern(normalized):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_COMPOUND_DIRECTIVE,
        }

    if _contains_reporting_bracket_mention(message):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_QUOTED_REPORTED,
        }

    if _is_quoted_or_backtick_wrapped(message):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_QUOTED_REPORTED,
        }

    if _is_reported_quoted_directive(message):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_QUOTED_REPORTED,
        }

    if _MALFORMED_DIRECTIVE_LOOKALIKE_PATTERN.fullmatch(message):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_MALFORMED_DIRECTIVE,
        }

    if _has_obvious_multi_sentence_boundary(message):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_MULTI_SENTENCE,
        }

    normalized_candidate = _normalize_candidate(message)
    if normalized_candidate.startswith("i prefer ") and (
        " because " in normalized_candidate or " and i prefer " in normalized_candidate
    ):
        return {
            "outcome": _DRAFT_OUTCOME_UNKNOWN,
            "directive": None,
            "reason": _REASON_SEMANTIC_UNCERTAINTY,
        }
    normalized_candidate = _rewrite_bounded_candidate(normalized_candidate)

    if (
        len(normalized_candidate) >= 2
        and normalized_candidate[0] in "\"'`(["
        and normalized_candidate[-1] in "\"'`)]"
        and (normalized_candidate[0], normalized_candidate[-1]) not in _WRAPPER_PAIRS
    ):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_MALFORMED_DIRECTIVE,
        }

    if _matches_multi_segment_pattern(normalized_candidate):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_COMPOUND_DIRECTIVE,
        }

    if _is_ambiguous_alias(normalized_candidate):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_COMPOUND_DIRECTIVE,
        }

    if _is_incomplete_directive(normalized_candidate):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_INCOMPLETE_DIRECTIVE,
        }

    if _is_unsupported_alias(normalized_candidate):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_MALFORMED_DIRECTIVE,
        }

    if _has_multiple_directive_starts(normalized_candidate):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_COMPOUND_DIRECTIVE,
        }

    decomposed = decompose_directive(normalized_candidate)
    if isinstance(decomposed, CanonicalDirective):
        return {
            "outcome": _DRAFT_OUTCOME_DIRECTIVE,
            "directive": decomposed,
        }

    if decomposed is not None:
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": (
                _REASON_INCOMPLETE_DIRECTIVE
                if _is_incomplete_directive(normalized_candidate)
                else _REASON_MALFORMED_DIRECTIVE
            ),
        }

    if _DIRECTIVE_REWRITE_CUE_PATTERN.match(normalized_candidate):
        return {
            "outcome": _DRAFT_OUTCOME_REJECTED,
            "directive": None,
            "reason": _REASON_MALFORMED_DIRECTIVE,
        }

    return {
        "outcome": _DRAFT_OUTCOME_UNKNOWN,
        "directive": None,
        "reason": _REASON_SEMANTIC_UNCERTAINTY,
    }
