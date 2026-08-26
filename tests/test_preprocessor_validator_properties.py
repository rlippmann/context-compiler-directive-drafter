from hypothesis import assume, given
from hypothesis import strategies as st

from context_compiler_directive_drafter.output_validation import (
    classify_drafter_output,
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

COMPOUND_SEPARATORS = st.sampled_from([" and ", "; ", "\n", ", then "])
STRUCTURED_NON_DIRECTIVE_CLASSIFICATIONS = st.sampled_from(["no_directive", "unknown"])


def test_validate_malformed_abstain_negative_boundaries_are_unknown() -> None:
    cases = {
        "<NO_DIRECT>": "unknown",
        "<NO_DIRECTION>": "unknown",
        "<NO_DIRECTIVE please>": "unknown",
        "notes: <NO_DIRECTIVE>": "unknown",
        "prefix <NO_DIRECTIPLE>": "unknown",
        "<NOT_DIRECTIVE>": "unknown",
        "<NO_DIRECTIPLE>": "unknown",
        "<NO_DIRECTIVE>": "no_directive",
    }
    for raw, expected_cls in cases.items():
        validated = classify_drafter_output(raw)
        assert validated["classification"] == expected_cls
        assert validated["output"] is None


@given(
    st.one_of(
        st.none(), st.integers(), st.text(max_size=120), st.dictionaries(st.text(), st.none())
    )
)
def test_validate_output_always_has_null_for_non_directive(raw_output: object) -> None:
    validated = classify_drafter_output(raw_output)
    if validated["classification"] == "directive":
        assert isinstance(validated["output"], str)
    else:
        assert validated["output"] is None


@given(
    st.sampled_from(CANONICAL_DIRECTIVES),
    COMPOUND_SEPARATORS,
    st.sampled_from(CANONICAL_DIRECTIVES),
)
def test_validate_compound_candidate_output_is_always_unknown(
    first: str, separator: str, second: str
) -> None:
    assume(first != second)
    validated = classify_drafter_output(f"{first}{separator}{second}")
    assert validated == {"classification": "unknown", "output": None}


@given(
    STRUCTURED_NON_DIRECTIVE_CLASSIFICATIONS,
    st.one_of(
        st.none(), st.text(max_size=80), st.integers(), st.dictionaries(st.text(), st.none())
    ),
)
def test_validate_structured_non_directive_contract_requires_null_output(
    classification: str, output: object
) -> None:
    validated = classify_drafter_output({"classification": classification, "output": output})
    if output is None:
        assert validated == {"classification": classification, "output": None}
    else:
        assert validated == {"classification": "unknown", "output": None}
