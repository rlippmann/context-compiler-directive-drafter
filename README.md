# Context Compiler Directive Drafter

Turn natural-language requests into candidate Context Compiler directives.

`context-compiler-directive-drafter` helps hosts translate user requests like:

> Please use Docker for container examples.

into candidate directives, such as:

> use docker

This package drafts suggestions for the Context Compiler. Only `context-compiler` applies directives and updates state.

The drafter suggests candidate directives. context-compiler decides what to do with them.

---

## When To Use It

Use this package when you want to:

- Translate user requests into safe, canonical directives.
- Avoid accidental or unsafe state changes from ambiguous input.
- Add a conservative natural-language-to-directive step before applying changes.

## Installation

Install in your host environment:

```bash
pip install "context-compiler-directive-drafter"
```

For local development:

```bash
uv sync --group dev
```


## Basic Usage

Draft and validate a candidate directive:

```python
from context_compiler_directive_drafter import preprocess_heuristic, parse_preprocessor_output

user_message = "Please use Docker for container examples."
result = preprocess_heuristic(user_message)

candidate = parse_preprocessor_output(
    result["directive"],
    source_input=user_message,
)

if candidate is not None:
    print("Candidate directive:", candidate)
else:
    print("No canonical directive found.")
```

The host validates drafted output before passing it to engine.step(...).

For small runnable examples, see [examples/basic_usage.py](examples/basic_usage.py)
and [examples/prompt_rendering.py](examples/prompt_rendering.py).

## Public API

Public interface:

- `preprocess_heuristic(message)`: Heuristically draft a candidate directive.
- `parse_preprocessor_output(raw_output, *, source_input=None)`: Validate and parse drafting output.
- `validate_preprocessor_output(raw_output, *, source_input=None)`: Classify raw output as directive, no_directive, or unknown.
- `render_prompt(path, state)`: Load and fill prompt templates.
- Constants and sentinels exported from the package.

## Recommended Host Flow

1. Run `preprocess_heuristic(message)`.
2. If a candidate exists, validate it with `parse_preprocessor_output(...)`.
3. If not valid, consider fallback drafting (e.g., LLM prompt).
4. Always validate fallback output with `parse_preprocessor_output(..., source_input=message)`.
5. If validation yields a directive, pass it to `context-compiler`.
6. Otherwise, pass the original user input unchanged.

**Safety Guidance:**

- Always validate drafting output before compiler handoff.
- Never pass raw model output directly to the compiler.
- Bypass drafting when clarification is pending.
- Do not edit `engine.state` directly.
- Prefer abstaining over unsafe rewrites.

Do not pass raw model output to the compiler.

## Prompt Resources

The package includes prompt templates for integrations that use model-based drafting when heuristic drafting does not produce a result.

- prompts/default.txt: recommended default prompt
- prompts/llama.txt: stricter prompt for Llama-family models

Use render_prompt(path, state) to load a template and fill it with the current compiler state.

The rendered prompt can be sent to an LLM to attempt directive drafting when heuristic drafting does not produce a result.

Any model output should still be validated with parse_preprocessor_output(...) or validate_preprocessor_output(...) before it is used.

## Current Limits

This package is intentionally conservative. It abstains when input is:

- Ambiguous, mixed-intent, or quoted.
- Embedded in prose, markdown, or code.
- Not matching a canonical directive form.

Boundary rules:

- Process the full message, not fragments.
- Emit at most one canonical directive.
- Do not mine surrounding prose for commands.
- Do not split multi-instruction input.
- Avoid broad semantic rewrites.
- Prefer false negatives over false positives.

Hosts that want broader proposal behavior should implement it explicitly.

## CLI

The CLI command is `directive-drafter`. The CLI currently supports a limited set of behaviors:

```bash
uv run directive-drafter "please make replies concise"
```

It returns a non-zero exit status and explains that a broader natural-language drafting workflow is not yet exposed as a user-facing CLI command.

## Development

Run local checks:

```bash
uv run pre-commit run --all-files
uv run pytest
```


## License

Apache-2.0
