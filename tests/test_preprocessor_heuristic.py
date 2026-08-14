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
        "allow docker",
        "set policy peanuts prohibit",
        "stop using peanuts",
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
        assert result["outcome"] == "unknown"
        assert result["directive"] is None
        assert result["reason"] is not None


def test_heuristic_rejects_structural_near_miss_alias_forms() -> None:
    cases = [
        ("allow podman", "reject.near_miss_alias"),
        ("stop using shell scripts", "reject.near_miss_alias"),
        ("set policy almonds prohibit", "reject.near_miss_alias"),
        ("use instead of pytest", "reject.near_miss_alias"),
        ("use uv not pip", "reject.near_miss_alias"),
        ("wipe policies", "reject.near_miss_alias"),
        ("reset policy", "reject.admin_near_miss_alias"),
        ("remove policies shell", "reject.admin_near_miss_alias"),
    ]
    for message, reason in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
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
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.quoted_exact",
        }


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
        "outcome": "no_directive",
        "directive": None,
        "reason": "reject.confident_non_directive",
    }


def test_heuristic_rejects_directive_adjacent_question_mark_as_unknown() -> None:
    cases = [
        "use docker?",
        "clear state?",
        "can you use pytest instead of unittest?",
    ]
    for message in cases:
        result = preprocess_heuristic(message)
        assert result["outcome"] == "unknown"
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
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.meta_or_reporting",
        }


def test_heuristic_rejects_reported_quoted_directives_structurally() -> None:
    cases = [
        'The docs say: "clear state".',
        'Alice wrote: "use docker".',
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.quoted_reported",
        }


def test_heuristic_rejects_list_or_enumeration_inputs() -> None:
    cases = [
        "1. use docker",
        "- clear state",
        "* prohibit peanuts",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.list_or_enumeration",
        }


def test_heuristic_rejects_multi_segment_or_mixed_prose_inputs() -> None:
    cases = [
        "use docker because this repo already has Docker",
        "clear state then continue",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.multi_segment_or_mixed_prose",
        }


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
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }


def test_heuristic_does_not_reject_single_directive_payload_with_ordinary_and() -> None:
    _assert_directive_result(preprocess_heuristic("use bread and butter"), "use bread and butter")


def test_heuristic_lexical_boundary_does_not_create_false_second_directive_start() -> None:
    assert preprocess_heuristic("misuse docker and prohibitively expensive peanuts") == {
        "outcome": "no_directive",
        "directive": None,
        "reason": "reject.confident_non_directive",
    }


def test_heuristic_rejects_malformed_replacement_syntax() -> None:
    cases = [
        "use podman instead docker",
        "use podman in stead of docker",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.malformed_replacement_syntax",
        }


def test_heuristic_rejects_admin_near_miss_aliases() -> None:
    cases = [
        "reset policy",
        "remove policies docker",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.admin_near_miss_alias",
        }


def test_heuristic_rejects_notes_and_reporting_with_bracketed_mentions() -> None:
    cases = [
        "In my notes: [clear state] [reset policies]",
        "Notes: [use docker] [prohibit peanuts]",
        "I wrote down [change premise to concise replies] yesterday",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.quoted_reported_bracket",
        }


def test_heuristic_accepts_bracket_wrapper_without_reporting_marker() -> None:
    _assert_directive_result(preprocess_heuristic("[clear state]"), "clear state")


def test_heuristic_set_premise_to_forms_are_unknown_not_rewritten() -> None:
    cases = [
        "set premise to concise replies",
        "set premise to formal tone",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }


def test_heuristic_dont_use_forms_are_unknown_not_rewritten() -> None:
    cases = [
        "don't use peanuts",
        "do not use peanuts",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }


def test_heuristic_does_not_canonicalize_set_premise_to_with_empty_payload() -> None:
    assert preprocess_heuristic("set premise to   ") == {
        "outcome": "unknown",
        "directive": None,
        "reason": "reject.directive_adjacent_unsafe",
    }


def test_heuristic_does_not_canonicalize_set_premise_to_when_not_whole_message() -> None:
    assert preprocess_heuristic("please set premise to concise replies") == {
        "outcome": "unknown",
        "directive": None,
        "reason": "reject.directive_adjacent_unsafe",
    }


def test_heuristic_change_premise_missing_to_forms_are_unknown_not_rewritten() -> None:
    cases = [
        "change premise concise replies",
        "change premise formal tone",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }


def test_heuristic_does_not_canonicalize_change_premise_with_empty_payload() -> None:
    assert preprocess_heuristic("change premise   ") == {
        "outcome": "unknown",
        "directive": None,
        "reason": "reject.directive_adjacent_unsafe",
    }


def test_heuristic_does_not_canonicalize_change_premise_when_not_whole_message() -> None:
    assert preprocess_heuristic("please change premise concise replies") == {
        "outcome": "unknown",
        "directive": None,
        "reason": "reject.directive_adjacent_unsafe",
    }


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
        "please use docker",
        "set premise to concise replies",
        "change premise concise replies",
        "do not use peanuts",
    ]
    for message in cases:
        result = preprocess_heuristic(message)
        assert result["outcome"] != "directive"
        assert result["directive"] is None


def test_heuristic_unknown_directive_like_text_remains_non_canonical() -> None:
    result = preprocess_heuristic("set policy peanuts prohibit")
    assert result == {
        "outcome": "unknown",
        "directive": None,
        "reason": "reject.near_miss_alias",
    }


def test_heuristic_returns_unknown_for_unresolved_cases() -> None:
    unresolved = ["Could we maybe use uv later"]

    for message in unresolved:
        assert preprocess_heuristic(message) == {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }


def test_heuristic_returns_no_directive_for_ordinary_non_directive_content() -> None:
    cases = [
        "not sure this is right",
        "thanks for the help",
    ]
    for message in cases:
        assert preprocess_heuristic(message) == {
            "outcome": "no_directive",
            "directive": None,
            "reason": "reject.confident_non_directive",
        }


def test_replacement_acquisition_guard_handles_non_string_item_operand() -> None:
    directive = CanonicalDirective(
        text="use docker",
        kind=DirectiveKind.USE_ITEM,
        operands=MappingProxyType({"item": object()}),
    )

    assert heuristic_module._looks_like_unsafe_replacement_acquisition_case(directive) is False


@pytest.mark.parametrize("message", ['""', "''", "()", "[]", "``"])
def test_heuristic_empty_wrappers_do_not_produce_directive(message: str) -> None:
    result = preprocess_heuristic(message)
    assert result["directive"] is None
