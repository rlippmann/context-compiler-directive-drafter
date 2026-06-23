"""Minimal package-owned example for heuristic drafting and validation."""

from context_compiler_directive_drafter import (
    parse_preprocessor_output,
    preprocess_heuristic,
)


def main() -> None:
    user_message = "use docker"
    result = preprocess_heuristic(user_message)

    print("heuristic result:", result)

    candidate = parse_preprocessor_output(
        result["directive"],
        source_input=user_message,
    )
    print("validated candidate:", candidate)

    ambiguous_message = "Can you use docker?"
    ambiguous_result = preprocess_heuristic(ambiguous_message)
    ambiguous_candidate = parse_preprocessor_output(
        ambiguous_result["directive"],
        source_input=ambiguous_message,
    )

    print("ambiguous result:", ambiguous_result)
    print("ambiguous candidate:", ambiguous_candidate)


if __name__ == "__main__":
    main()
