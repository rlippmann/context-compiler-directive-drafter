import json
from collections import Counter
from pathlib import Path

import pytest
from context_compiler.grammar import decompose_directive

_CORPUS_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "corpus"
    / "english"
    / "directive-drafter-en.jsonl"
)
_FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "preprocessor"
_CLASSIFICATIONS = {"CONTRACT", "EVALUATION", "BOTH"}
_OUTCOMES = {"directive", "no_directive", "unknown"}
_PATHS = {"heuristic", "fallback", "either"}
_CATEGORIES = {
    "canonical_exact",
    "bounded_rewrite",
    "preference_statement",
    "hedged_request",
    "question",
    "quoted_reported",
    "single_sentence_mixed_intent",
    "multi_sentence_host_boundary",
    "incomplete_ambiguous_replacement",
    "alias",
    "ordinary_prose",
    "payload_boundary",
}
_DOMAINS = {
    "software_development",
    "food_preferences",
    "writing_style",
    "project_workflow",
    "travel_planning",
    "everyday_preferences_policies",
    "health",
    "finance",
    "legal",
    "household_home",
    "education_learning",
    "accessibility",
    "communication_etiquette",
    "shopping_product_preferences",
    "scheduling_time_management",
    "media_content_preferences",
    "family_social_planning",
}
_REQUIRED_KEYS = {
    "id",
    "language",
    "classification",
    "input",
    "expected_outcome",
    "expected_directive",
    "expected_path",
    "category",
    "domain",
    "rationale",
}


def _load_cases() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in _CORPUS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_contract_fixtures() -> dict[str, dict[str, object]]:
    fixtures: dict[str, dict[str, object]] = {}
    for path in _FIXTURES_PATH.glob("*.json"):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture.get("kind", "heuristic") == "heuristic":
            fixtures[fixture["name"]] = fixture
    return fixtures


def test_english_corpus_schema_and_contract_links() -> None:
    cases = _load_cases()
    fixtures = _load_contract_fixtures()
    ids: set[str] = set()

    assert len(cases) >= 100
    for case in cases:
        assert set(case) >= _REQUIRED_KEYS, case
        assert isinstance(case["id"], str) and case["id"].strip(), case
        assert case["id"] not in ids, case["id"]
        ids.add(case["id"])
        assert case["language"] == "en", case["id"]
        assert case["classification"] in _CLASSIFICATIONS, case["id"]
        assert case["expected_outcome"] in _OUTCOMES, case["id"]
        assert case["expected_path"] in _PATHS, case["id"]
        assert case["category"] in _CATEGORIES, case["id"]
        assert case["domain"] in _DOMAINS, case["id"]
        assert isinstance(case["input"], str) and case["input"].strip(), case["id"]
        assert isinstance(case["rationale"], str) and case["rationale"].strip(), case["id"]

        if case["expected_outcome"] == "directive":
            directive = case["expected_directive"]
            assert isinstance(directive, str) and directive
            assert decompose_directive(directive) is not None, case["id"]
        else:
            assert case["expected_directive"] is None, case["id"]

        fallback_expectation = case.get("fallback_expectation")
        if fallback_expectation is not None:
            assert isinstance(fallback_expectation, dict), case["id"]
            preferred_outcome = fallback_expectation.get("preferred_outcome")
            acceptable_outcomes = fallback_expectation.get("acceptable_outcomes")
            assert preferred_outcome in _OUTCOMES, case["id"]
            assert isinstance(acceptable_outcomes, list), case["id"]
            assert set(acceptable_outcomes) <= _OUTCOMES, case["id"]
            assert preferred_outcome in acceptable_outcomes, case["id"]
            preferred_directive = fallback_expectation.get("preferred_directive")
            if preferred_directive is not None:
                assert preferred_outcome == "directive", case["id"]
                assert isinstance(preferred_directive, str)
                assert decompose_directive(preferred_directive) is not None, case["id"]

        contract_ref = case.get("contract_ref")
        if contract_ref is None:
            continue
        assert case["classification"] in {"CONTRACT", "BOTH"}, case["id"]
        assert isinstance(contract_ref, str) and contract_ref in fixtures, case["id"]
        fixture = fixtures[contract_ref]
        assert case["input"] == fixture["input"], case["id"]
        expected = fixture["expected"]
        assert case["expected_outcome"] == expected["outcome"], case["id"]
        if case["expected_outcome"] == "directive":
            assert case["expected_directive"] == expected["directive"]["text"], case["id"]


def test_english_corpus_covers_required_dimensions() -> None:
    cases = _load_cases()
    by_domain = Counter(case["domain"] for case in cases)
    by_category = Counter(case["category"] for case in cases)
    by_classification = Counter(case["classification"] for case in cases)

    assert set(by_domain) == _DOMAINS
    assert min(by_domain.values()) >= 12
    assert set(by_category) == _CATEGORIES
    assert min(by_category.values()) >= 4
    assert set(by_classification) == _CLASSIFICATIONS
    assert by_classification["EVALUATION"] > by_classification["CONTRACT"]


def test_english_corpus_supports_offline_filtering() -> None:
    cases = _load_cases()

    english_cases = [case for case in cases if case["language"] == "en"]
    travel_cases = [case for case in cases if case["domain"] == "travel_planning"]
    contract_cases = [case for case in cases if case["classification"] in {"CONTRACT", "BOTH"}]

    assert len(english_cases) == len(cases)
    assert len(travel_cases) >= 17
    assert contract_cases
    assert all(case["language"] == "en" for case in english_cases)
    assert all(case["domain"] == "travel_planning" for case in travel_cases)
    assert all(case["classification"] in {"CONTRACT", "BOTH"} for case in contract_cases)


@pytest.mark.parametrize("case_id", ["en-software-greeting-use-001", "en-food-greeting-avoid-001"])
def test_greeting_directive_adjacent_cases_remain_fallback_eligible(case_id: str) -> None:
    case = next(case for case in _load_cases() if case["id"] == case_id)
    assert case["expected_outcome"] == "unknown"
    assert case["expected_path"] in {"fallback", "either"}
