import json
from pathlib import Path

import context_compiler_directive_drafter as preprocessor

_CONTRACT_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "preprocessor" / "public-api-v1.json"
)


def _load_contract() -> dict[str, object]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


_EXPECTED_RUNTIME_EXPORTS = [
    "PREPROCESSOR_NO_DIRECTIVE_SENTINEL",
    "PREPROCESS_OUTCOME_DIRECTIVE",
    "PREPROCESS_OUTCOME_NO_DIRECTIVE",
    "PREPROCESS_OUTCOME_UNKNOWN",
    "preprocess_heuristic",
    "validate_preprocessor_output",
    "parse_preprocessor_output",
    "render_prompt",
]

_TYPING_ONLY_NAMES = [
    "PreprocessOutcome",
    "PreprocessResult",
]


def test_preprocessor_api_contract_fixture_matches_public_surface() -> None:
    contract = _load_contract()

    assert contract["kind"] == "api-contract"
    assert set(contract["required_exports"]) == set(_EXPECTED_RUNTIME_EXPORTS)

    for name in contract["required_exports"]:
        assert hasattr(preprocessor, name), name
        assert name in preprocessor.__all__, name


def test_preprocessor_api_contract_fixture_has_unique_entries() -> None:
    contract = _load_contract()

    required_exports = contract["required_exports"]
    assert len(required_exports) == len(set(required_exports))


def test_preprocessor_api_contract_fixture_excludes_typing_only_names() -> None:
    contract = _load_contract()

    for name in _TYPING_ONLY_NAMES:
        assert name not in contract["required_exports"], name


def test_preprocessor_module_does_not_export_typing_only_names() -> None:
    for name in _TYPING_ONLY_NAMES:
        assert not hasattr(preprocessor, name), name
        assert name not in preprocessor.__all__, name
