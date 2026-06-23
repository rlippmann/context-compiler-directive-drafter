"""Minimal package-owned example for rendering a packaged prompt."""

from importlib.resources import as_file, files

from context_compiler import create_engine

from context_compiler_directive_drafter import render_prompt


def main() -> None:
    engine = create_engine()
    engine.step("set premise concise replies")
    engine.step("use docker")
    engine.step("prohibit peanuts")

    prompt_resource = files("context_compiler_directive_drafter").joinpath("prompts/default.txt")
    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, engine.state)

    if rendered is None:
        raise RuntimeError("prompt resource could not be loaded")

    print("\n".join(rendered.splitlines()[:8]))


if __name__ == "__main__":
    main()
