"""Run the English Directive Drafter corpus through a live fallback adapter.

This module is intentionally an evaluation tool, not a conformance authority.
The corpus remains evaluation data and the public ``DirectiveDrafter`` API
remains responsible for heuristic/fallback routing.
"""

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO, cast

from context_compiler.grammar import CanonicalDirective

from context_compiler_directive_drafter import (
    DirectiveDrafter,
    RejectedDirective,
    UnknownDirective,
    create_openai_fallback,
)
from context_compiler_directive_drafter.drafter import DraftResult

DraftFallback = Callable[[str, str], str | None]

DEFAULT_CORPUS_PATH = (
    Path(__file__).resolve().parents[1] / "corpus" / "english" / "directive-drafter-en.jsonl"
)
DEFAULT_RESULTS_PATH = Path("eval-results/directive-drafter-en.jsonl")

CorpusCase = dict[str, object]
ResultRecord = dict[str, object]


@dataclass
class FallbackObserver:
    """Capture callback invocation facts without inspecting fallback output."""

    invocation_count: int = 0
    raw_responses: list[str | None] = field(default_factory=list)

    def wrap(self, fallback: DraftFallback) -> DraftFallback:
        def observed(user_input: str, prompt: str) -> str | None:
            self.invocation_count += 1
            response = fallback(user_input, prompt)
            self.raw_responses.append(response)
            return response

        return observed

    def case_observation(self, start_count: int, start_response_count: int) -> dict[str, object]:
        responses = self.raw_responses[start_response_count:]
        return {
            "fallback_invoked": self.invocation_count > start_count,
            "fallback_invocation_count": self.invocation_count - start_count,
            "raw_fallback_response": responses[-1] if responses else None,
            "raw_fallback_responses": responses,
        }


def load_corpus(path: Path = DEFAULT_CORPUS_PATH) -> list[CorpusCase]:
    """Load non-empty JSONL corpus records from ``path``."""

    return [
        cast(CorpusCase, json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_cases(
    cases: Iterable[CorpusCase],
    *,
    domains: Sequence[str] = (),
    categories: Sequence[str] = (),
    case_ids: Sequence[str] = (),
    limit: int | None = None,
) -> list[CorpusCase]:
    """Apply optional domain, category, id, and limit filters in corpus order."""

    selected = list(cases)
    if domains:
        selected = [case for case in selected if case.get("domain") in domains]
    if categories:
        selected = [case for case in selected if case.get("category") in categories]
    if case_ids:
        selected = [case for case in selected if case.get("id") in case_ids]
    if limit is not None:
        selected = selected[:limit]
    return selected


def _actual_variant(result: DraftResult) -> tuple[str, str | None]:
    if isinstance(result.result, CanonicalDirective):
        return "directive", result.result.text
    if isinstance(result.result, RejectedDirective):
        return "rejected", None
    if isinstance(result.result, UnknownDirective):
        return "unknown", None
    raise TypeError(f"Unsupported DraftResult variant: {type(result.result)!r}")


def _failure(category: str, reason: str) -> tuple[str, str]:
    return category, reason


def _score_content(
    case: CorpusCase,
    actual_outcome: str,
    actual_directive: str | None,
    *,
    fallback_invoked: bool,
) -> tuple[str, str] | None:
    fallback_expectation = case.get("fallback_expectation")
    if fallback_invoked and isinstance(fallback_expectation, dict):
        acceptable_outcomes = cast(list[str], fallback_expectation["acceptable_outcomes"])
        if actual_outcome not in acceptable_outcomes:
            preferred_outcome = fallback_expectation["preferred_outcome"]
            if preferred_outcome == "directive":
                return _failure(
                    "missed_directive",
                    f"expected a directive or accepted abstention; got {actual_outcome}",
                )
            return _failure(
                "wrong_outcome",
                f"expected one of {acceptable_outcomes}; got {actual_outcome}",
            )

        preferred_directive = fallback_expectation.get("preferred_directive")
        if (
            preferred_directive is not None
            and actual_outcome == "directive"
            and actual_directive != preferred_directive
        ):
            return _failure(
                "wrong_directive",
                f"expected {preferred_directive!r}; got {actual_directive!r}",
            )
        return None

    expected_outcome = cast(str, case["expected_outcome"])
    expected_directive = cast(str | None, case["expected_directive"])
    if expected_outcome == "directive":
        if actual_outcome != "directive":
            return _failure("missed_directive", f"expected directive; got {actual_outcome}")
        if actual_directive != expected_directive:
            return _failure(
                "wrong_directive",
                f"expected {expected_directive!r}; got {actual_directive!r}",
            )
        return None
    if actual_outcome == "directive":
        return _failure("unexpected_directive", f"expected {expected_outcome}; got directive")
    if actual_outcome != expected_outcome:
        return _failure(
            "wrong_outcome",
            f"expected {expected_outcome}; got {actual_outcome}",
        )
    return None


def score_case(
    case: CorpusCase,
    result: DraftResult,
    *,
    fallback_invoked: bool = False,
    fallback_invocation_count: int = 0,
    raw_fallback_response: str | None = None,
    raw_fallback_responses: Sequence[str | None] = (),
) -> ResultRecord:
    """Score one public ``DraftResult`` and explicit routing observations."""

    actual_outcome, actual_directive = _actual_variant(result)
    actual_path = "fallback" if fallback_invoked else "heuristic"

    expected_path = cast(str, case["expected_path"])
    path_match = expected_path == "either" or actual_path == expected_path
    routing_contractual = (
        cast(str, case["classification"]) in {"CONTRACT", "BOTH"} and expected_path != "either"
    )
    routing_failure_category = "unexpected_source" if not path_match else None

    if (
        fallback_invoked
        and isinstance(result.result, RejectedDirective)
        and result.result.reason == "invalid_candidate"
    ):
        failure: tuple[str, str] | None = _failure(
            "invalid_candidate", "fallback output was not a canonical directive"
        )
    else:
        failure = _score_content(
            case,
            actual_outcome,
            actual_directive,
            fallback_invoked=fallback_invoked,
        )
    semantic_passed = failure is None
    passed = semantic_passed and not (routing_contractual and not path_match)

    record: ResultRecord = {
        "id": case["id"],
        "domain": case["domain"],
        "category": case["category"],
        "classification": case["classification"],
        "expected_outcome": case["expected_outcome"],
        "expected_directive": case["expected_directive"],
        "expected_path": case["expected_path"],
        "actual_path": actual_path,
        "path_match": path_match,
        "routing_contractual": routing_contractual,
        "routing_mismatch": not path_match,
        "actual_outcome": actual_outcome,
        "actual_directive": actual_directive,
        "actual_source": result.source,
        "fallback_invoked": fallback_invoked,
        "fallback_invocation_count": fallback_invocation_count,
        "raw_fallback_response": raw_fallback_response,
        "raw_fallback_responses": list(raw_fallback_responses),
        "semantic_passed": semantic_passed,
        "passed": passed,
        "failure_category": failure[0] if failure else None,
        "failure_reason": failure[1] if failure else None,
        "routing_failure_category": routing_failure_category,
    }
    return record


def run_cases(
    cases: Iterable[CorpusCase],
    fallback: DraftFallback,
    *,
    fallback_source: str = "openai-compatible",
) -> list[ResultRecord]:
    """Wrap fallback, then run selected cases through public ``DirectiveDrafter``."""

    observer = FallbackObserver()
    drafter = DirectiveDrafter(
        fallback=observer.wrap(fallback),
        fallback_source=fallback_source,
    )
    records: list[ResultRecord] = []
    for case in cases:
        start_count = observer.invocation_count
        start_response_count = len(observer.raw_responses)
        try:
            result = drafter.draft_directive(cast(str, case["input"]))
        except Exception as error:  # noqa: BLE001 - live evals should continue after one case fails.
            observation = observer.case_observation(start_count, start_response_count)
            actual_path = "fallback" if observation["fallback_invoked"] else "heuristic"
            records.append(
                {
                    "id": case["id"],
                    "domain": case["domain"],
                    "category": case["category"],
                    "classification": case["classification"],
                    "expected_outcome": case["expected_outcome"],
                    "expected_directive": case["expected_directive"],
                    "expected_path": case["expected_path"],
                    "actual_path": actual_path,
                    "path_match": case["expected_path"] in {"either", actual_path},
                    "routing_contractual": (
                        cast(str, case["classification"]) in {"CONTRACT", "BOTH"}
                        and case["expected_path"] != "either"
                    ),
                    "routing_mismatch": case["expected_path"] not in {"either", actual_path},
                    "actual_outcome": "error",
                    "actual_directive": None,
                    "actual_source": "error",
                    **observation,
                    "semantic_passed": False,
                    "passed": False,
                    "failure_category": "fallback_error",
                    "failure_reason": f"{type(error).__name__}: {error}",
                    "routing_failure_category": None,
                }
            )
            continue
        records.append(
            score_case(
                case,
                result,
                **observer.case_observation(start_count, start_response_count),
            )
        )
    return records


def _group_results(records: Iterable[ResultRecord], field: str) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for record in records:
        key = cast(str, record[field])
        counts = grouped.setdefault(key, {"total": 0, "passed": 0, "failed": 0})
        counts["total"] += 1
        counts["passed" if record["passed"] else "failed"] += 1
    return dict(sorted(grouped.items()))


def summarize_results(records: Iterable[ResultRecord]) -> dict[str, object]:
    """Build machine-readable aggregate counts for result records."""

    records = list(records)
    failure_categories = Counter(
        cast(str, record["failure_category"])
        for record in records
        if record["failure_category"] is not None
    )
    routing_failure_categories = Counter(
        cast(str, record["routing_failure_category"])
        for record in records
        if record["routing_failure_category"] is not None
    )
    return {
        "total": len(records),
        "passed": sum(bool(record["passed"]) for record in records),
        "failed": sum(not bool(record["passed"]) for record in records),
        "heuristic_handled": sum(record["actual_source"] == "heuristic" for record in records),
        "fallback_invoked": sum(bool(record["fallback_invoked"]) for record in records),
        "fallback_invocation_count": sum(
            int(record["fallback_invocation_count"]) for record in records
        ),
        "path_mismatches": sum(bool(record["routing_mismatch"]) for record in records),
        "contractual_path_mismatches": sum(
            bool(record["routing_mismatch"]) and bool(record["routing_contractual"])
            for record in records
        ),
        "results_by_domain": _group_results(records, "domain"),
        "results_by_category": _group_results(records, "category"),
        "failure_categories": dict(sorted(failure_categories.items())),
        "routing_failure_categories": dict(sorted(routing_failure_categories.items())),
    }


def write_results(path: Path, records: Iterable[ResultRecord]) -> None:
    """Write detailed result records as JSONL, creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, sort_keys=True) + "\n")


def print_report(records: Iterable[ResultRecord], output: TextIO = sys.stdout) -> None:
    """Print a concise human-readable evaluation report."""

    records = list(records)
    summary = summarize_results(records)
    print(
        "total={total} passed={passed} failed={failed} "
        "heuristic_handled={heuristic_handled} fallback_invoked={fallback_invoked} "
        "fallback_invocation_count={fallback_invocation_count} "
        "path_mismatches={path_mismatches}".format(**summary),
        file=output,
    )
    for label, summary_field in (
        ("domain", "results_by_domain"),
        ("category", "results_by_category"),
    ):
        print(f"results by {label}:", file=output)
        for name, counts in cast(dict[str, dict[str, int]], summary[summary_field]).items():
            print(
                f"  {name}: {counts['passed']}/{counts['total']} passed",
                file=output,
            )
    print("failure categories:", file=output)
    failures = cast(dict[str, int], summary["failure_categories"])
    if failures:
        for category, count in failures.items():
            print(f"  {category}: {count}", file=output)
    else:
        print("  none", file=output)
    print(
        "routing mismatches: "
        f"{summary['path_mismatches']} "
        f"({summary['contractual_path_mismatches']} contractual)",
        file=output,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="directive-drafter-en-eval",
        description="Run the English Directive Drafter corpus through a live fallback.",
    )
    parser.add_argument("--model", required=True, help="OpenAI-compatible model name.")
    parser.add_argument(
        "--base-url", help="Optional OpenAI-compatible API base URL, such as an Ollama endpoint."
    )
    parser.add_argument(
        "--api-key",
        help="Optional API key; otherwise OPENAI_API_KEY is passed through when set.",
    )
    parser.add_argument("--domain", action="append", dest="domains", help="Filter by domain.")
    parser.add_argument(
        "--category", action="append", dest="categories", help="Filter by category."
    )
    parser.add_argument("--case-id", action="append", dest="case_ids", help="Filter by case id.")
    parser.add_argument("--limit", type=int, help="Run at most this many selected cases.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help=f"JSONL result path (default: {DEFAULT_RESULTS_PATH}).",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS_PATH,
        help="Corpus JSONL path override for local evaluation data.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 0:
        raise SystemExit("--limit must be non-negative")

    cases = select_cases(
        load_corpus(args.corpus),
        domains=args.domains or (),
        categories=args.categories or (),
        case_ids=args.case_ids or (),
        limit=args.limit,
    )
    if not cases:
        print("No corpus cases matched the selected filters.", file=sys.stderr)
        return 2

    api_key = args.api_key if args.api_key is not None else os.environ.get("OPENAI_API_KEY")
    try:
        fallback = create_openai_fallback(
            model=args.model,
            api_key=api_key,
            base_url=args.base_url,
        )
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2

    records = run_cases(
        cases,
        fallback,
        fallback_source="openai-compatible",
    )
    print_report(records)
    write_results(args.output, records)
    print(f"detailed results: {args.output}")
    return 0 if all(bool(record["passed"]) for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
