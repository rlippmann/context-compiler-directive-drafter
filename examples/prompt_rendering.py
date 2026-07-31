"""Minimal package-owned example for rendering a packaged prompt."""

from importlib.resources import as_file, files

from context_compiler import PolicyValue

from context_compiler_directive_drafter import render_prompt


def main() -> None:
    premise = "concise replies"
    policies: dict[str, PolicyValue] = {
        "docker": "use",
        "peanuts": "prohibit",
    }

    prompt_resource = files("context_compiler_directive_drafter").joinpath("prompts/default.txt")
    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, premise, policies)

    if rendered is None:
        raise RuntimeError("prompt resource could not be loaded")

    print("\n".join(rendered.splitlines()[:8]))


if __name__ == "__main__":
    main()
