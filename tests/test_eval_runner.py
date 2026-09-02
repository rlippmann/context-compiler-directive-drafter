import io
import json
from pathlib import Path

import pytest
from context_compiler.grammar import decompose_directive

import evals.runners.directive_drafter_en as runner
from context_compiler_directive_drafter import DraftResult, RejectedDirective
from evals.runners.directive_drafter_en import (
    build_parser,
    load_corpus,
    print_report,
    run_cases,
    score_case,
    select_cases,
    summarize_results,
    write_results,
)


def _canonical(text: str):
    result = decompose_directive(text)
    assert result is not None
    return result


def _case(**overrides: object) -> dict[str, object]:
    case: dict[str, object] = {
        "id": "case-1",
        "domain": "software_development",
        "category": "canonical_exact",
        "classification": "CONTRACT",
        "expected_outcome": "directive",
        "expected_directive": "use docker",
        "expected_path": "heuristic",
        "input": "use docker",
    }
    case.update(overrides)
    return case


def test_load_and_select_cases_support_filters_and_limit(tmp_path: Path) -> None:
    path = tmp_path / "corpus.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(_case(id="one", category="canonical_exact")),
                json.dumps(_case(id="two", domain="food_preferences", category="alias")),
                json.dumps(_case(id="three", domain="food_preferences", category="alias")),
            ]
        ),
        encoding="utf-8",
    )

    cases = load_corpus(path)

    assert [case["id"] for case in select_cases(cases, domains=["food_preferences"], limit=1)] == [
        "two"
    ]
    assert [
        case["id"] for case in select_cases(cases, categories=["alias"], case_ids=["three"])
    ] == ["three"]


def test_heuristic_handled_case_uses_normal_expectations() -> None:
    case = _case(
        expected_outcome="rejected",
        expected_directive=None,
        fallback_expectation={
            "preferred_outcome": "directive",
            "preferred_directive": "use podman",
            "acceptable_outcomes": ["directive", "unknown"],
        },
    )

    record = score_case(
        case,
        DraftResult(source="heuristic", result=RejectedDirective(reason="non_directive")),
        fallback_invoked=False,
    )

    assert record["semantic_passed"] is True
    assert record["passed"] is True
    assert record["fallback_invoked"] is False


def test_fallback_invocation_and_raw_response_are_recorded() -> None:
    case = _case(
        id="unknown",
        input="Could we maybe use uv later",
        expected_outcome="unknown",
        expected_directive=None,
        expected_path="fallback",
        fallback_expectation={
            "preferred_outcome": "directive",
            "preferred_directive": "use podman",
            "acceptable_outcomes": ["directive", "unknown"],
        },
    )
    calls: list[str] = []

    def fallback(user_input: str) -> str:
        calls.append(user_input)
        return "use podman"

    records = run_cases([case], fallback)

    assert calls == ["Could we maybe use uv later"]
    assert records[0]["fallback_invoked"] is True
    assert records[0]["fallback_invocation_count"] == 1
    assert records[0]["raw_fallback_response"] == "use podman"
    assert records[0]["raw_fallback_responses"] == ["use podman"]


def test_heuristic_handled_case_does_not_invoke_fallback() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> str:
        calls.append(user_input)
        return "use podman"

    records = run_cases([_case(input="use docker")], fallback)

    assert calls == []
    assert records[0]["fallback_invoked"] is False
    assert records[0]["fallback_invocation_count"] == 0
    assert records[0]["raw_fallback_response"] is None


def test_invalid_candidate_preserves_raw_model_text() -> None:
    case = _case(
        input="Could we maybe use uv later",
        expected_outcome="unknown",
        expected_directive=None,
        expected_path="fallback",
        fallback_expectation={
            "preferred_outcome": "unknown",
            "acceptable_outcomes": ["unknown", "rejected"],
        },
    )

    records = run_cases([case], lambda _: "not a canonical directive")

    assert records[0]["failure_category"] == "invalid_candidate"
    assert records[0]["raw_fallback_response"] == "not a canonical directive"
    assert records[0]["actual_outcome"] == "rejected"


def test_article_only_directive_difference_is_semantically_equivalent() -> None:
    case = _case(
        expected_directive="use the weekly quiz instead of the old quiz",
        fallback_expectation={
            "preferred_outcome": "directive",
            "preferred_directive": "use the weekly quiz instead of the old quiz",
            "acceptable_outcomes": ["directive", "unknown"],
        },
    )

    record = score_case(
        case,
        DraftResult(source="fallback", result=_canonical("use weekly quiz instead of old quiz")),
        fallback_invoked=True,
    )

    assert record["semantic_passed"] is True


def test_meaningful_directive_difference_is_not_equivalent() -> None:
    case = _case(
        expected_directive="use the weekly quiz instead of the old quiz",
        fallback_expectation={
            "preferred_outcome": "directive",
            "preferred_directive": "use the weekly quiz instead of the old quiz",
            "acceptable_outcomes": ["directive", "unknown"],
        },
    )

    record = score_case(
        case,
        DraftResult(source="fallback", result=_canonical("use weekly quiz")),
        fallback_invoked=True,
    )

    assert record["failure_category"] == "wrong_directive"


def test_article_normalization_preserves_plan_identifier() -> None:
    case = _case(expected_directive="use plan A")

    record = score_case(
        case,
        DraftResult(source="fallback", result=_canonical("use plan")),
        fallback_invoked=True,
    )

    assert record["failure_category"] == "wrong_directive"


def test_article_normalization_preserves_vitamin_identifier() -> None:
    case = _case(expected_directive="use vitamin A")

    record = score_case(
        case,
        DraftResult(source="fallback", result=_canonical("use vitamin")),
        fallback_invoked=True,
    )

    assert record["failure_category"] == "wrong_directive"


def test_article_normalization_preserves_capitalized_the_who() -> None:
    case = _case(expected_directive="use The Who")

    record = score_case(
        case,
        DraftResult(source="fallback", result=_canonical("use Who")),
        fallback_invoked=True,
    )

    assert record["failure_category"] == "wrong_directive"


def test_article_normalization_preserves_capitalized_the_thing() -> None:
    case = _case(expected_directive="use The Thing")

    record = score_case(
        case,
        DraftResult(source="fallback", result=_canonical("use Thing")),
        fallback_invoked=True,
    )

    assert record["failure_category"] == "wrong_directive"


def test_semantic_pass_with_path_mismatch_is_reported_separately() -> None:
    case = _case(
        classification="EVALUATION",
        expected_path="fallback",
    )

    record = score_case(
        case,
        DraftResult(source="heuristic", result=_canonical("use docker")),
        fallback_invoked=False,
    )

    assert record["semantic_passed"] is True
    assert record["passed"] is True
    assert record["actual_path"] == "heuristic"
    assert record["path_match"] is False
    assert record["routing_mismatch"] is True
    assert record["failure_category"] is None
    assert record["routing_failure_category"] == "unexpected_source"


def test_contractual_path_mismatch_is_explicit_and_distinct() -> None:
    case = _case(classification="BOTH", expected_path="fallback")

    record = score_case(
        case,
        DraftResult(source="heuristic", result=_canonical("use docker")),
        fallback_invoked=False,
    )

    assert record["routing_contractual"] is True
    assert record["routing_mismatch"] is True
    assert record["semantic_passed"] is True
    assert record["passed"] is False
    assert record["failure_category"] is None


def test_summary_counts_contractual_routing_mismatch_as_failed() -> None:
    evaluation_record = score_case(
        _case(classification="EVALUATION", expected_path="fallback"),
        DraftResult(source="heuristic", result=_canonical("use docker")),
        fallback_invoked=False,
    )
    contractual_record = score_case(
        _case(id="contractual", classification="BOTH", expected_path="fallback"),
        DraftResult(source="heuristic", result=_canonical("use docker")),
        fallback_invoked=False,
    )

    summary = summarize_results([evaluation_record, contractual_record])

    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["path_mismatches"] == 2
    assert summary["contractual_path_mismatches"] == 1


def test_acceptable_fallback_abstention_passes_and_records_none_response() -> None:
    case = _case(
        input="Could we maybe use uv later",
        expected_outcome="unknown",
        expected_directive=None,
        expected_path="fallback",
        fallback_expectation={
            "preferred_outcome": "directive",
            "preferred_directive": "use podman",
            "acceptable_outcomes": ["directive", "unknown", "rejected"],
        },
    )

    records = run_cases([case], lambda _: None)

    assert records[0]["semantic_passed"] is True
    assert records[0]["fallback_invoked"] is True
    assert records[0]["raw_fallback_response"] is None


def test_summary_fallback_count_uses_callback_observation() -> None:
    cases = [
        _case(id="heuristic", input="use docker"),
        _case(
            id="fallback",
            input="Could we maybe use uv later",
            expected_outcome="unknown",
            expected_directive=None,
            expected_path="fallback",
            fallback_expectation={
                "preferred_outcome": "unknown",
                "acceptable_outcomes": ["unknown", "rejected"],
            },
        ),
    ]

    records = run_cases(cases, lambda _: None)
    summary = summarize_results(records)

    assert summary["heuristic_handled"] == 1
    assert summary["fallback_invoked"] == 1
    assert summary["fallback_invocation_count"] == 1


def test_summary_report_and_jsonl_output(tmp_path: Path) -> None:
    records = [
        score_case(
            _case(),
            DraftResult(source="heuristic", result=_canonical("use docker")),
        ),
        score_case(
            _case(id="two", expected_outcome="rejected", expected_directive=None),
            DraftResult(source="heuristic", result=_canonical("use docker")),
        ),
    ]
    summary = summarize_results(records)
    output = io.StringIO()
    print_report(records, output)
    path = tmp_path / "eval-results" / "results.jsonl"
    write_results(path, records)

    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["heuristic_handled"] == 2
    assert "results by domain:" in output.getvalue()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_parser_exposes_live_runner_configuration() -> None:
    args = build_parser().parse_args(
        [
            "--model",
            "test-model",
            "--base-url",
            "http://localhost/v1",
            "--domain",
            "health",
            "--category",
            "question",
            "--case-id",
            "case-1",
            "--limit",
            "2",
            "--output",
            "eval-results/test.jsonl",
        ]
    )

    assert args.model == "test-model"
    assert args.transport == "openai-compatible"
    assert args.base_url == "http://localhost/v1"
    assert args.domains == ["health"]
    assert args.categories == ["question"]
    assert args.case_ids == ["case-1"]
    assert args.limit == 2
    assert args.output == Path("eval-results/test.jsonl")


def test_parser_selects_litellm_transport_and_provider_model() -> None:
    args = build_parser().parse_args(
        ["--model", "anthropic/claude-sonnet-4-5", "--transport", "litellm"]
    )

    assert args.model == "anthropic/claude-sonnet-4-5"
    assert args.transport == "litellm"


def test_main_routes_litellm_model_and_endpoint_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_factory(**kwargs: object):
        captured.update(kwargs)
        return lambda _: None

    def fake_run_cases(cases, fallback, *, fallback_source):
        captured["fallback_source"] = fallback_source
        captured["fallback"] = fallback
        return [{"passed": True}]

    monkeypatch.setattr(runner, "load_corpus", lambda _: [_case(input="use docker")])
    monkeypatch.setattr(runner, "create_litellm_fallback", fake_factory)
    monkeypatch.setattr(runner, "run_cases", fake_run_cases)
    monkeypatch.setattr(runner, "print_report", lambda _: None)
    monkeypatch.setattr(runner, "write_results", lambda *_: None)

    assert (
        runner.main(
            [
                "--transport",
                "litellm",
                "--model",
                "anthropic/claude-sonnet-4-5",
                "--api-key",
                "key",
                "--base-url",
                "https://proxy.example",
                "--output",
                str(tmp_path / "results.jsonl"),
            ]
        )
        == 0
    )
    assert captured["model"] == "anthropic/claude-sonnet-4-5"
    assert captured["api_key"] == "key"
    assert captured["api_base"] == "https://proxy.example"
    assert captured["fallback_source"] == "litellm"
