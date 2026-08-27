"""Minimal package-owned example for high-level directive drafting."""

from context_compiler_directive_drafter import DirectiveDrafter, RejectedDirective, UnknownDirective


def main() -> None:
    result = DirectiveDrafter().draft_directive("Please use Docker for container examples.")

    if hasattr(result.result, "text"):
        print("candidate directive:", result.result.text)
    elif isinstance(result.result, RejectedDirective):
        print("directive acquisition rejected:", result.result.reason)
    elif isinstance(result.result, UnknownDirective):
        print("need clarification before drafting:", result.result.reason)


if __name__ == "__main__":
    main()
