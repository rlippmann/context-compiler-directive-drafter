"""Minimal package-owned example for heuristic drafting and fallback validation."""

from context_compiler.grammar import CanonicalDirective, decompose_directive

from context_compiler_directive_drafter import (
    classify_drafter_output,
    preprocess_heuristic,
)


def main() -> None:
    user_message = "use docker"
    result = preprocess_heuristic(user_message)

    print(
        "heuristic result:",
        {
            "outcome": result["outcome"],
            "directive": result["directive"].text if result["outcome"] == "directive" else None,
        },
    )

    candidate = result["directive"] if result["outcome"] == "directive" else None
    print("heuristic candidate:", candidate.text if candidate is not None else None)

    ambiguous_message = "Can you use docker?"
    ambiguous_result = preprocess_heuristic(ambiguous_message)
    ambiguous_candidate = (
        ambiguous_result["directive"] if ambiguous_result["outcome"] == "directive" else None
    )

    print("ambiguous result:", ambiguous_result)
    print(
        "ambiguous candidate:",
        ambiguous_candidate.text if ambiguous_candidate is not None else None,
    )

    validated = classify_drafter_output("use podman")
    assert validated["classification"] == "directive"
    validated_output = validated["output"]
    assert isinstance(validated_output, str)
    fallback_candidate = decompose_directive(validated_output)
    assert isinstance(fallback_candidate, CanonicalDirective)
    print(
        "fallback candidate:",
        fallback_candidate.text if fallback_candidate is not None else None,
    )


if __name__ == "__main__":
    main()
