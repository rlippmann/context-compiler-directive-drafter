"""Minimal package-owned example for heuristic drafting and validation."""

from context_compiler_directive_drafter import (
    parse_preprocessor_output,
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
    print("validated candidate:", candidate.text if candidate is not None else None)

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

    fallback_candidate = parse_preprocessor_output("use podman")
    print(
        "fallback candidate:",
        fallback_candidate.text if fallback_candidate is not None else None,
    )


if __name__ == "__main__":
    main()
