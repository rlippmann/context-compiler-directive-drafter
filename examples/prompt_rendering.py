"""Minimal package-owned example for rendering a packaged prompt."""

from importlib.resources import as_file, files

from context_compiler import State

from context_compiler_directive_drafter import render_prompt


def main() -> None:
    state: State = {
        "premise": "concise replies",
        "policies": {
            "docker": "use",
            "peanuts": "prohibit",
        },
        "version": 2,
    }

    prompt_resource = files("context_compiler_directive_drafter").joinpath("prompts/default.txt")
    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, state)

    if rendered is None:
        raise RuntimeError("prompt resource could not be loaded")

    print("\n".join(rendered.splitlines()[:8]))


if __name__ == "__main__":
    main()
