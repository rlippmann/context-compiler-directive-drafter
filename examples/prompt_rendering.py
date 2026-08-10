"""Minimal package-owned example for loading the shared converter prompt."""

from context_compiler_directive_drafter import get_converter_prompt


def main() -> None:
    prompt = get_converter_prompt()
    print("\n".join(prompt.splitlines()[:26]))


if __name__ == "__main__":
    main()
