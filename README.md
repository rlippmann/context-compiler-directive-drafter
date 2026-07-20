# Context Compiler Directive Drafter

Turn natural-language requests into candidate Context Compiler directives.

`context-compiler-directive-drafter` helps hosts translate user requests like:

> Please use Docker for container examples.

into candidate directives, such as:

> use docker

This package drafts suggestions for the Context Compiler. Only `context-compiler` applies directives and updates state.

The drafter suggests candidate directives. context-compiler decides what to do with them.

The drafter owns the human-facing acquisition step between messy user input and
canonical directive text. That includes deciding when a message is close enough
to propose a canonical directive, when the message is not a directive at all,
and when the message is too unclear or malformed to safely interpret without
more help. The drafter may use optional read-only interpretation context to
resolve references and narrow likely user intent, but it does not become an
authority over state, permissions, or application.

---

## When To Use It

Use this package when you want to:

- Translate user requests into safe, canonical directives.
- Handle near-canonical input, alternate phrasing, and malformed-but-recoverable
  directive attempts before compiler handoff.
- Distinguish "no directive" from "unknown or failed interpretation" in a
  stable host-facing contract.
- Avoid accidental or unsafe state changes from ambiguous input.
- Add a conservative natural-language-to-directive step before applying changes.

This package owns the human-facing acquisition boundary, including when to propose a canonical directive, when to abstain, and when to ask for clarification or interpretation confirmation before compiler handoff.

The normative acquisition contract lives in [docs/DrafterAcquisitionSpec.md](docs/DrafterAcquisitionSpec.md).
This package does not own:

- authoritative compiler state
- the decision about whether a canonical directive is allowed in the current
  context
- directive application or state mutation
- invention of new directive semantics beyond the compiler-owned contract

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
- `parse_preprocessor_output(raw_output)`: Validate and parse drafting output.
- `validate_preprocessor_output(raw_output)`: Classify raw output as directive, no_directive, or unknown.
- `render_prompt(path, state)`: Load and fill prompt templates.
- Constants and sentinels exported from the package.

### Output Contract

The intended acquisition boundary is:

- input: user text plus optional read-only interpretation context
- output: one of `directive`, `no_directive`, or `unknown`

Every drafting path should end in one of three host-visible outcomes:

- `directive`: a canonical directive string that is ready for compiler review
  and independent policy checks
- `no_directive`: the input is not asking for a directive
- `unknown`: the input appears directive-related or interpretation failed, but
  the drafter should not guess

`directive` means "this is a proposed canonical directive," not "this directive
is permitted" and not "this directive has been applied."

Optional interpretation context exists to help the drafter resolve references,
compare the user's wording against currently active directives, and safely
narrow likely intent. That context is read-only and interpretive. It does not
authorize the drafter to validate, mutate, or apply authoritative state.

## Recommended Host Flow

1. Run `preprocess_heuristic(message)`.
2. If a candidate exists, validate it with `parse_preprocessor_output(...)`.
3. If not valid, consider fallback drafting (e.g., LLM prompt).
4. Always validate fallback output with `parse_preprocessor_output(...)`.
5. If validation yields `directive`, pass that canonical directive to
   `context-compiler` for authoritative review and application.
6. If validation yields `no_directive`, continue the host flow without a
   directive handoff.
7. If validation yields `unknown`, preserve the boundary: ask for
   clarification, show resubmission guidance, or retry drafting in a safer
   workflow.

**Safety Guidance:**

- Always validate drafting output before compiler handoff.
- Never pass raw model output directly to the compiler.
- Bypass drafting when clarification is pending.
- Do not edit `engine.state` directly.
- Prefer abstaining over unsafe guesses.
- Use interpretation context to resolve human references only when that context
  is read-only and supplied for drafting.
- Output validation checks the canonical directive contract, not whether the
  directive is allowed in context.
- A structurally valid drafted directive may still be the wrong interpretation of the user's meaning.
- Reviewed semantic drafting belongs in a separate higher-level workflow.

Hosts may use the `unknown` outcome to trigger clarification, confirmation, or
resubmission guidance. That interaction is part of the human-input drafting
boundary, but any eventual canonical directive must still be revalidated before
compiler handoff.

### Interpretation Example

The drafter may use read-only context to interpret intent without becoming a
state authority.

Example:

- user input: `use Linux instead of Windows`
- interpretation context: `Windows is not currently present`
- possible drafter output: `use Linux`

In that example, the drafter uses context to narrow the likely user intent into
a canonical directive that core can review. The drafter still does not mutate
state, does not authorize the operation, and does not decide whether the
resulting directive is valid to apply. Core remains responsible for validating
and applying the resulting canonical directive.

Do not pass raw model output to the compiler.

## Prompt Resources

The package includes prompt templates for integrations that use model-based drafting when heuristic drafting does not produce a result.

- prompts/default.txt: recommended default prompt
- prompts/llama.txt: stricter prompt for Llama-family models

Use render_prompt(path, state) to load a template and fill it with the current compiler state snapshot.

The rendered prompt can be sent to an LLM to attempt directive drafting when heuristic drafting does not produce a result.

Any model output should still be validated with parse_preprocessor_output(...) or validate_preprocessor_output(...) before it is shown or used.

## Current Limits

This package is intentionally conservative. It abstains or returns `unknown`
when input is:

- Ambiguous, mixed-intent, or quoted.
- Embedded in prose, markdown, or code.
- Not safely interpretable as one canonical directive.

Boundary rules:

- Process the full message, not fragments.
- Emit at most one canonical directive.
- Abstain when one message contains multiple directive-shaped instructions.
- Do not mine surrounding prose for commands.
- Do not split one message into multiple drafted directives.
- Do not invent new directive semantics.
- Avoid broad semantic rewrites that effectively create new policy meaning.
- Prefer false negatives over false positives.

`context-compiler-directive-drafter` only proposes at most one candidate
directive. `context-compiler` remains responsible for independently enforcing
the single-directive invariant before any authoritative application.

The drafter should consume the compiler-owned grammar contract once that
extracted contract is available. This package should not duplicate or become
the normative owner of grammar rules in its own documentation or prompt
resources.

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
