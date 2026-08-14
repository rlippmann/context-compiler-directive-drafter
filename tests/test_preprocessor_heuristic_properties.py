import re

from context_compiler.grammar import decompose_directive, get_directive_metadata
from hypothesis import assume, given
from hypothesis import strategies as st

from context_compiler_directive_drafter import heuristic_preprocessor as heuristic_module
from context_compiler_directive_drafter import preprocess_heuristic
from context_compiler_directive_drafter.constants import (
    DRAFT_OUTCOME_DIRECTIVE,
    DRAFT_OUTCOME_NO_DIRECTIVE,
    DRAFT_OUTCOME_UNKNOWN,
)
from context_compiler_directive_drafter.output_validation import (
    parse_preprocessor_output,
)

CANONICAL_DIRECTIVES = [
    "set premise concise replies",
    "change premise to formal tone",
    "use docker",
    "prohibit peanuts",
    "remove policy docker",
    "use podman instead of docker",
    "clear premise",
    "reset policies",
    "clear state",
]

NON_EMPTY_TEXT = st.text(min_size=1, max_size=40).filter(lambda s: s.strip() != "")
WRAPPERS = st.sampled_from(
    [
        ("(", ")"),
        ("[", "]"),
    ]
)
QUOTED_WRAPPERS = st.sampled_from(
    [
        ('"', '"'),
        ("'", "'"),
        ("`", "`"),
    ]
)
COMPOUND_SEPARATORS = st.sampled_from([" and ", "; ", "\n", ", then "])
CANONICAL_LOOKALIKE_WORDS = st.sampled_from(
    [
        "and butter",
        "and clear examples",
        "for prohibitively expensive cases",
        "for removal-policy notes",
        "near reset-policy docs",
    ]
)
CANONICAL_STARTS = tuple({metadata.canonical_start for metadata in get_directive_metadata()})
DIRECTIVE_FRAGMENTS = tuple({cue for cue in heuristic_module._directive_cues() if " " not in cue})


@given(st.sampled_from(CANONICAL_DIRECTIVES), st.sampled_from([".", "!"]))
def test_heuristic_accepts_canonical_directive_with_trailing_period_or_bang(
    directive: str, punctuation: str
) -> None:
    result = preprocess_heuristic(f"{directive}{punctuation}")
    assert result["outcome"] == DRAFT_OUTCOME_DIRECTIVE
    assert result["directive"].text == directive
    parsed = parse_preprocessor_output(result["directive"])
    assert parsed is not None
    assert parsed is result["directive"]


@given(st.sampled_from(CANONICAL_DIRECTIVES))
def test_heuristic_question_suffix_never_produces_directive(directive: str) -> None:
    result = preprocess_heuristic(f"{directive}?")
    assert result["outcome"] == DRAFT_OUTCOME_UNKNOWN
    assert result["directive"] is None


@given(st.sampled_from(CANONICAL_DIRECTIVES), WRAPPERS)
def test_heuristic_accepts_single_layer_exact_wrapper(
    directive: str, wrapper: tuple[str, str]
) -> None:
    left, right = wrapper
    result = preprocess_heuristic(f"{left}{directive}{right}")
    assert result["outcome"] == DRAFT_OUTCOME_DIRECTIVE
    assert result["directive"].text == directive
    parsed = parse_preprocessor_output(result["directive"])
    assert parsed is not None
    assert parsed is result["directive"]


@given(st.sampled_from(CANONICAL_DIRECTIVES), QUOTED_WRAPPERS)
def test_heuristic_quoted_exact_wrappers_never_directive(
    directive: str, wrapper: tuple[str, str]
) -> None:
    left, right = wrapper
    result = preprocess_heuristic(f"{left}{directive}{right}")
    assert result["outcome"] == DRAFT_OUTCOME_UNKNOWN
    assert result["directive"] is None


@given(
    st.sampled_from(CANONICAL_DIRECTIVES),
    WRAPPERS,
    st.sampled_from(["example:", "for example", "i said", "he said", "the command is"]),
)
def test_heuristic_rejects_wrapped_directive_with_surrounding_meta_text(
    directive: str, wrapper: tuple[str, str], prefix: str
) -> None:
    left, right = wrapper
    message = f"{prefix} {left}{directive}{right}"
    result = preprocess_heuristic(message)
    assert result["outcome"] != DRAFT_OUTCOME_DIRECTIVE


@given(st.text(max_size=60), st.text(max_size=60))
def test_heuristic_question_mark_is_always_rejected(prefix: str, suffix: str) -> None:
    message = f"{prefix}?{suffix}"
    result = preprocess_heuristic(message)
    assert result["outcome"] in {DRAFT_OUTCOME_NO_DIRECTIVE, DRAFT_OUTCOME_UNKNOWN}
    assert result["directive"] is None


@given(st.text(max_size=120))
def test_heuristic_directive_output_is_always_validator_safe(message: str) -> None:
    result = preprocess_heuristic(message)
    if result["outcome"] != DRAFT_OUTCOME_DIRECTIVE:
        return
    directive = result["directive"]
    assert directive.text
    parsed = parse_preprocessor_output(directive)
    assert parsed is not None
    assert parsed is directive


@given(st.sampled_from(CANONICAL_DIRECTIVES), NON_EMPTY_TEXT, NON_EMPTY_TEXT)
def test_heuristic_whole_message_discipline_for_surrounded_directive(
    directive: str, prefix: str, suffix: str
) -> None:
    message = f"{prefix} {directive} {suffix}"
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    assume(prefix.strip() not in {'"', "'", "`", "(", "["})
    assume(suffix.strip() not in {'"', "'", "`", ")", "]"})
    assume(not message.strip().lower().startswith("change premise "))
    assume(decompose_directive(normalized) is None)
    result = preprocess_heuristic(message)
    assert result["outcome"] != DRAFT_OUTCOME_DIRECTIVE


@given(NON_EMPTY_TEXT)
def test_heuristic_list_or_enumeration_prefix_never_directive(rest: str) -> None:
    for prefix in ("1. ", "- ", "* "):
        result = preprocess_heuristic(f"{prefix}{rest}")
        assert result["outcome"] != DRAFT_OUTCOME_DIRECTIVE


@given(st.sampled_from(CANONICAL_DIRECTIVES))
def test_heuristic_meta_reporting_prefix_never_directive(directive: str) -> None:
    samples = [
        f"example: {directive}",
        f"for example {directive}",
        f"the command is {directive}",
        f'i said "{directive}"',
        f'he said "{directive}"',
    ]
    for message in samples:
        result = preprocess_heuristic(message)
        assert result["outcome"] != DRAFT_OUTCOME_DIRECTIVE


@given(st.sampled_from(["use docker", "clear state", "prohibit peanuts"]), NON_EMPTY_TEXT)
def test_heuristic_mixed_prose_connector_forms_never_directive(
    directive_seed: str, detail: str
) -> None:
    messages = [
        f"{directive_seed} because {detail}",
        f"{directive_seed} then continue {detail}",
        f"{directive_seed} and then continue {detail}",
        f"{directive_seed} and explain {detail}",
    ]
    for message in messages:
        result = preprocess_heuristic(message)
        assert result["outcome"] != DRAFT_OUTCOME_DIRECTIVE


@given(
    st.sampled_from(CANONICAL_DIRECTIVES),
    COMPOUND_SEPARATORS,
    st.sampled_from(CANONICAL_DIRECTIVES),
)
def test_heuristic_compound_directives_always_abstain(
    first: str, separator: str, second: str
) -> None:
    assume(first != second)
    result = preprocess_heuristic(f"{first}{separator}{second}")
    assert result["outcome"] == DRAFT_OUTCOME_UNKNOWN
    assert result["directive"] is None


@given(st.sampled_from(["use docker", "prohibit peanuts"]), CANONICAL_LOOKALIKE_WORDS)
def test_heuristic_singular_payload_with_canonical_looking_words_can_still_pass(
    directive_seed: str, suffix: str
) -> None:
    message = f"{directive_seed} {suffix}"
    result = preprocess_heuristic(message)
    assert result["outcome"] == DRAFT_OUTCOME_DIRECTIVE
    assert result["directive"].text == message


@given(st.sampled_from(["misuse", "re-use", "nonuse"]), NON_EMPTY_TEXT)
def test_heuristic_lexical_boundary_prevents_embedded_use_matches(prefix: str, suffix: str) -> None:
    result = preprocess_heuristic(f"{prefix} docker {suffix}")
    assert result["outcome"] != DRAFT_OUTCOME_DIRECTIVE


@given(st.sampled_from(CANONICAL_STARTS))
def test_heuristic_metadata_cues_cover_every_canonical_start(canonical_start: str) -> None:
    assert heuristic_module._contains_directive_cue(f"please {canonical_start} later")


@given(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Ll", "Lu", "Nd"),
            whitelist_characters=(" ",),
        ),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s.strip() != ""),
    st.sampled_from(DIRECTIVE_FRAGMENTS),
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Ll", "Lu", "Nd"),
            whitelist_characters=(" ",),
        ),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s.strip() != ""),
)
def test_ordinary_prose_with_directive_like_fragment_does_not_become_directive(
    prefix: str, fragment: str, suffix: str
) -> None:
    message = f"{prefix} {fragment} {suffix}"
    assume("?" not in message)
    assume(
        not re.match(
            r"^\s*(?:example:|for example\b|the command is\b|(?:i|he|she|they) said\b)",
            message.lower(),
        )
    )
    assume(not re.match(r"^\s*(?:\d+[.)]|[-*])\s+\S", message))

    result = preprocess_heuristic(message)
    assert result["outcome"] != DRAFT_OUTCOME_DIRECTIVE
