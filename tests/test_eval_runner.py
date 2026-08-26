import io
import json
from pathlib import Path

from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter import DraftResult, NoDirective, UnknownDirective
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


def test_score_case_accepts_fallback_expectation_and_preferred_directive() -> None:
    case = _case(
        expected_outcome="unknown",
        expected_directive=None,
        expected_path="fallback",
        fallback_expectation={
            "preferred_outcome": "directive",
            "preferred_directive": "use podman",
            "acceptable_outcomes": ["directive", "unknown"],
        },
    )

    record = score_case(
        case,
        DraftResult(source="openai-compatible", result=_canonical("use podman")),
    )

    assert record["passed"] is True
    assert record["failure_category"] is None


def test_score_case_reports_invalid_fallback_output() -> None:
    case = _case(
        expected_outcome="unknown",
        expected_directive=None,
        expected_path="fallback",
        fallback_expectation={
            "preferred_outcome": "unknown",
            "acceptable_outcomes": ["unknown", "no_directive"],
        },
    )

    record = score_case(
        case,
        DraftResult(
            source="openai-compatible",
            result=UnknownDirective(reason="invalid_canonical_directive"),
        ),
    )

    assert record["passed"] is False
    assert record["failure_category"] == "invalid_fallback_output"


def test_run_cases_uses_public_drafter_method_and_continues_after_error() -> None:
    class FakeDrafter:
        def __init__(self) -> None:
            self.inputs: list[str] = []

        def draft_directive(self, user_input: str) -> DraftResult:
            self.inputs.append(user_input)
            if user_input == "boom":
                raise RuntimeError("provider unavailable")
            return DraftResult(source="heuristic", result=NoDirective(reason="test"))

    drafter = FakeDrafter()
    records = run_cases(
        [
            _case(
                id="ordinary",
                input="ordinary",
                expected_outcome="no_directive",
                expected_directive=None,
                expected_path="heuristic",
            ),
            _case(
                id="error",
                input="boom",
                expected_outcome="unknown",
                expected_directive=None,
                expected_path="fallback",
            ),
        ],
        drafter,  # type: ignore[arg-type]
    )

    assert drafter.inputs == ["ordinary", "boom"]
    assert records[0]["passed"] is True
    assert records[1]["failure_category"] == "fallback_error"


def test_summary_report_and_jsonl_output(tmp_path: Path) -> None:
    records = [
        score_case(
            _case(),
            DraftResult(source="heuristic", result=_canonical("use docker")),
        ),
        score_case(
            _case(id="two", expected_outcome="no_directive", expected_directive=None),
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
    assert args.base_url == "http://localhost/v1"
    assert args.domains == ["health"]
    assert args.categories == ["question"]
    assert args.case_ids == ["case-1"]
    assert args.limit == 2
    assert args.output == Path("eval-results/test.jsonl")
