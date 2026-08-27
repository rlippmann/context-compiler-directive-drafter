from types import MappingProxyType, SimpleNamespace

import pytest
from context_compiler.grammar import CanonicalDirective, DirectiveKind

from context_compiler_directive_drafter import heuristic_preprocessor as heuristic_module
from context_compiler_directive_drafter import preprocess_heuristic


def _assert_directive_result(result: dict[str, object], expected: str) -> None:
    assert result["outcome"] == "directive"
    directive = result["directive"]
    assert isinstance(directive, CanonicalDirective)
    assert directive.text == expected


def test_heuristic_rejects_consistent_high_risk_non_directives() -> None:
    cases = [
        "use instead of docker",
        "use podman instead of",
        "use podman not docker",
        "wipe policies",
        "clear premise then clear state",
        "prohibit peanuts and use almonds",
        "set premise concise; reset policies",
        "use docker, actually prohibit docker",
        '"set premise concise replies" is invalid syntax, right?',
        'For example, you could "remove policy docker".',
        'He said "use docker".',
        'The doc literally says: "clear premise".',
    ]

    for message in cases:
        result = preprocess_heuristic(message)
        assert result["outcome"] == "rejected"
        assert result["directive"] is None
        assert result["reason"] is not None


def test_heuristic_rejects_structural_near_miss_alias_forms() -> None:
    cases = [
        ("use instead of pytest", "compound_directive"),
        ("use uv not pip", "compound_directive"),
        ("wipe policies", "malformed_directive"),
        ("reset policy", "malformed_directive"),
        ("remove policies shell", "malformed_directive"),
    ]
    for message, reason in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": reason,
        }


def test_heuristic_accepts_trailing_period_or_bang_for_whole_message_directives() -> None:
    cases = [
        ("clear state.", "clear state"),
        ("reset policies!", "reset policies"),
        ("use docker.", "use docker"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_allows_exact_full_message_wrappers_for_directives() -> None:
    cases = [
        ("(reset policies)", "reset policies"),
        ("[prohibit peanuts]", "prohibit peanuts"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_rejects_quoted_or_backticked_exact_directives() -> None:
    cases = [
        "`use docker`",
        '"clear state"',
        "'reset policies'",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "quoted_reported",
        }


def test_heuristic_distinguishes_quoted_command_from_quoted_operand() -> None:
    _assert_directive_result(preprocess_heuristic('use "docker"'), 'use "docker"')


def test_heuristic_case_normalizes_exact_command_shapes() -> None:
    cases = [
        ("CLEAR STATE", "clear state"),
        ("Use Docker", "use docker"),
        ("Prohibit Peanuts", "prohibit peanuts"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_question_mark_only_non_directive_is_confident() -> None:
    assert preprocess_heuristic("can you help with lunch?") == {
        "outcome": "rejected",
        "directive": None,
        "reason": "ordinary_non_directive",
    }


def test_heuristic_rejects_question_mark_after_directive_like_text() -> None:
    cases = [
        "use docker?",
        "clear state?",
        "can you use pytest instead of unittest?",
        "I prefer concise replies?",
    ]
    for message in cases:
        result = preprocess_heuristic(message)
        assert result["outcome"] == "rejected"
        assert result["directive"] is None
        assert result["reason"] is not None


def test_heuristic_rejects_meta_reporting_or_example_prefixes() -> None:
    cases = [
        "example: use docker",
        "the command is clear state",
        'I said "use docker"',
        'he said "reset policies"',
        'example: "use docker"',
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "quoted_reported",
        }


def test_heuristic_rejects_reported_quoted_directives_structurally() -> None:
    cases = [
        'The docs say: "clear state".',
        'Alice wrote: "use docker".',
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "quoted_reported",
        }


def test_heuristic_rejects_list_or_enumeration_inputs() -> None:
    cases = [
        "1. use docker",
        "- clear state",
        "* prohibit peanuts",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "unsupported_input",
        }


def test_heuristic_rejects_multi_segment_or_mixed_prose_inputs() -> None:
    cases = [
        "use docker because this repo already has Docker",
        "clear state then continue",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "compound_directive",
        }


def test_heuristic_rejects_obvious_multi_sentence_input_for_host_segmentation() -> None:
    for message in [
        "use oat milk. explain how it is made.",
        "use docker. then tell me why.",
        "please use docker. thanks.",
    ]:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "multi_sentence",
        }


def test_heuristic_keeps_decimal_and_abbreviation_punctuation_in_single_input() -> None:
    for message in ["use version 3.2", "use e.g. docker"]:
        result = preprocess_heuristic(message)
        assert result["outcome"] == "directive"
        assert result["directive"] is not None


def test_heuristic_directive_cues_follow_grammar_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        heuristic_module,
        "get_directive_metadata",
        lambda: (
            SimpleNamespace(canonical_start="adopt"),
            SimpleNamespace(canonical_start="drop"),
            SimpleNamespace(canonical_start="change premise to"),
        ),
    )

    assert heuristic_module._contains_directive_cue("can you adopt docker?") is True
    assert heuristic_module._contains_directive_cue("please change premise concise replies") is True
    assert heuristic_module._contains_directive_cue("use docker") is False


def test_heuristic_multi_segment_detection_follows_grammar_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        heuristic_module,
        "get_directive_metadata",
        lambda: (
            SimpleNamespace(canonical_start="adopt"),
            SimpleNamespace(canonical_start="drop"),
        ),
    )

    assert heuristic_module._matches_multi_segment_pattern("adopt docker because it helps") is True
    assert heuristic_module._matches_multi_segment_pattern("use docker because it helps") is False


def test_heuristic_rejects_multiple_canonical_directive_starts() -> None:
    cases = [
        "use docker and prohibit peanuts",
        "prohibit peanuts; use docker",
        "set premise deployment target is staging, then use cautious rollout",
        "clear premise and reset policies",
        "remove policy docker\nuse podman",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "compound_directive",
        }


def test_heuristic_does_not_reject_single_directive_payload_with_ordinary_and() -> None:
    _assert_directive_result(preprocess_heuristic("use bread and butter"), "use bread and butter")


def test_heuristic_lexical_boundary_does_not_create_false_second_directive_start() -> None:
    assert preprocess_heuristic("misuse docker and prohibitively expensive peanuts") == {
        "outcome": "unknown",
        "directive": None,
        "reason": "semantic_uncertainty",
    }


def test_heuristic_rejects_incomplete_or_ambiguous_replacement_syntax() -> None:
    cases = [
        ("use instead of docker", "compound_directive"),
        ("use podman instead of", "incomplete_directive"),
        ("use podman not docker", "compound_directive"),
    ]
    for message, reason in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": reason,
        }


def test_heuristic_rejects_admin_near_miss_aliases() -> None:
    cases = [
        "reset policy",
        "remove policies docker",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "malformed_directive",
        }


def test_heuristic_rejects_notes_and_reporting_with_bracketed_mentions() -> None:
    cases = [
        "In my notes: [clear state] [reset policies]",
        "Notes: [use docker] [prohibit peanuts]",
        "I wrote down [change premise to concise replies] yesterday",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "quoted_reported",
        }


def test_heuristic_accepts_bracket_wrapper_without_reporting_marker() -> None:
    _assert_directive_result(preprocess_heuristic("[clear state]"), "clear state")


def test_heuristic_rewrites_set_premise_to_forms() -> None:
    cases = [
        ("set premise to concise replies", "set premise concise replies"),
        ("set premise to formal tone", "set premise formal tone"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_rewrites_prohibition_aliases() -> None:
    cases = [
        ("don't use peanuts", "prohibit peanuts"),
        ("do not use peanuts", "prohibit peanuts"),
        ("stop using peanuts", "prohibit peanuts"),
        ("set policy peanuts prohibit", "prohibit peanuts"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_does_not_canonicalize_set_premise_to_with_empty_payload() -> None:
    assert preprocess_heuristic("set premise to   ") == {
        "outcome": "rejected",
        "directive": None,
        "reason": "incomplete_directive",
    }


def test_heuristic_rewrites_polite_set_premise_to_form() -> None:
    _assert_directive_result(
        preprocess_heuristic("please set premise to concise replies"),
        "set premise concise replies",
    )


def test_heuristic_rewrites_clear_preference_forms() -> None:
    cases = [
        ("I prefer concise replies", "use concise replies"),
        ("I prefer oat milk in coffee", "use oat milk in coffee"),
        ("I prefer scenic routes", "use scenic routes"),
        ("I prefer morning appointments", "use morning appointments"),
        ("I prefer index funds", "use index funds"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_does_not_reduce_ambiguous_preference_forms() -> None:
    cases = [
        "I prefer",
        "I prefer concise replies because they are easier to scan",
        "I prefer concise replies and I prefer detailed examples",
    ]
    for message in cases:
        result = preprocess_heuristic(message)
        assert result["outcome"] == "unknown"
        assert result["directive"] is None


def test_heuristic_rewrites_change_premise_missing_to_forms() -> None:
    cases = [
        ("change premise concise replies", "change premise to concise replies"),
        ("change premise formal tone", "change premise to formal tone"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_does_not_canonicalize_change_premise_with_empty_payload() -> None:
    assert preprocess_heuristic("change premise   ") == {
        "outcome": "rejected",
        "directive": None,
        "reason": "incomplete_directive",
    }


def test_heuristic_rewrites_polite_change_premise_form() -> None:
    _assert_directive_result(
        preprocess_heuristic("please change premise concise replies"),
        "change premise to concise replies",
    )


def test_heuristic_does_not_strip_please_from_mixed_prose() -> None:
    result = preprocess_heuristic("please use docker because containers are nice")
    assert result == {
        "outcome": "rejected",
        "directive": None,
        "reason": "compound_directive",
    }


def test_heuristic_rewrites_allow_alias_and_replacement_syntax() -> None:
    cases = [
        ("allow docker", "use docker"),
        ("use podman instead docker", "use podman instead of docker"),
        ("use podman in stead of docker", "use podman instead of docker"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_accepts_strict_canonical_directives() -> None:
    directives = [
        "set premise concise replies",
        "change premise to concise replies",
        "use docker",
        "prohibit peanuts",
        "remove policy docker",
        "use podman instead of docker",
        "clear premise",
        "reset policies",
        "clear state",
    ]

    for directive in directives:
        result = preprocess_heuristic(directive)
        _assert_directive_result(result, directive)
        assert isinstance(result["directive"], CanonicalDirective)
        assert result["directive"].text == directive


def test_heuristic_normalizes_mixed_case_payload_before_core_parsing() -> None:
    result = preprocess_heuristic("Use Docker")

    assert result["outcome"] == "directive"
    directive = result["directive"]
    assert isinstance(directive, CanonicalDirective)
    assert directive.text == "use docker"
    assert directive.operands["item"] == "docker"


def test_heuristic_results_preserve_canonical_directive_object() -> None:
    result = preprocess_heuristic("use docker")

    assert result["outcome"] == "directive"
    assert isinstance(result["directive"], CanonicalDirective)
    assert result["directive"].text == "use docker"


def test_heuristic_directive_output_is_grammar_validated_not_regex_only() -> None:
    result = preprocess_heuristic("use docker")
    assert result["outcome"] == "directive"
    assert isinstance(result["directive"], CanonicalDirective)
    assert result["directive"].text == "use docker"
    assert result["directive"].kind is DirectiveKind.USE_ITEM


def test_heuristic_directive_shaped_text_does_not_bypass_grammar_validation() -> None:
    cases = [
        ("please use docker", "use docker"),
        ("set premise to concise replies", "set premise concise replies"),
        ("change premise concise replies", "change premise to concise replies"),
        ("do not use peanuts", "prohibit peanuts"),
    ]
    for message, expected in cases:
        _assert_directive_result(preprocess_heuristic(message), expected)


def test_heuristic_unknown_directive_like_text_remains_non_canonical() -> None:
    result = preprocess_heuristic("wipe policies")
    assert result == {
        "outcome": "rejected",
        "directive": None,
        "reason": "malformed_directive",
    }


def test_heuristic_returns_unknown_for_unresolved_cases() -> None:
    unresolved = ["Could we maybe use uv later", "not sure this is right"]

    for message in unresolved:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "semantic_uncertainty",
        }


def test_heuristic_returns_no_directive_for_ordinary_non_directive_content() -> None:
    cases = [
        "thanks for the help",
        "Hi",
        "Hello!",
        "Thank you",
        "Good morning",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "rejected",
            "directive": None,
            "reason": "ordinary_non_directive",
        }


def test_heuristic_does_not_ignore_directive_adjacent_text_after_greeting() -> None:
    for message in (
        "Hi, please use Docker",
        "Thanks, use Docker",
        "Hello, maybe avoid peanuts",
    ):
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "semantic_uncertainty",
        }


def test_canonical_directive_rejects_non_string_item_operand() -> None:
    with pytest.raises(ValueError, match="Operand 'item' for use_item must be a string"):
        CanonicalDirective(
            kind=DirectiveKind.USE_ITEM,
            operands=MappingProxyType({"item": object()}),
        )


@pytest.mark.parametrize("message", ['""', "''", "()", "[]", "``"])
def test_heuristic_empty_wrappers_do_not_produce_directive(message: str) -> None:
    result = preprocess_heuristic(message)
    assert result["directive"] is None
