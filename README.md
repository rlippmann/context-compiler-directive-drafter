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
more help. It does not become an authority over state, permissions, or
application.

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

Draft a candidate directive:

```python
from context_compiler_directive_drafter import DirectiveDrafter
from context_compiler_directive_drafter import NoDirective, UnknownDirective

drafter = DirectiveDrafter()

result = drafter.draft_directive(
    "Please use Docker for container examples.",
)

if hasattr(result.result, "text"):
    print("Candidate directive:", result.result.text)
elif isinstance(result.result, NoDirective):
    print("No canonical directive drafted:", result.result.reason)
elif isinstance(result.result, UnknownDirective):
    print("Need clarification before drafting:", result.result.reason)
```

The host validates drafted output before passing it to engine.step(...).

For small runnable examples, see [examples/basic_usage.py](examples/basic_usage.py)
and [examples/prompt_rendering.py](examples/prompt_rendering.py).

## Public API

Public interface:

- `DirectiveDrafter()`: Synchronous orchestration over heuristic preprocessing, optional fallback acquisition, fallback output parsing and validation, and final result construction.
- `DraftResult`: Structured non-authoritative result returned by `DirectiveDrafter.draft_directive(...)`.
- `NoDirective` and `UnknownDirective`: Non-canonical drafting result variants with preserved reasons.
- `preprocess_heuristic(message)`: Heuristically draft a candidate directive and, on success, return the `CanonicalDirective` directly.
- `parse_preprocessor_output(raw_output)`: Parse fallback candidate output into a `CanonicalDirective` when valid.
- `validate_preprocessor_output(raw_output)`: Classify raw output as directive, no_directive, or unknown.
- `get_converter_prompt()`: Load the shared static converter system prompt.
- Constants and sentinels exported from the package.

### Output Contract

The intended drafting boundary is:

- input: user text
- output: `DraftResult(source=<final producer>, result=<drafting-layer variant>)`

Every drafting path should end in one of three host-visible result variants:

- `CanonicalDirective`: a proposed canonical directive that is ready for compiler review and independent policy checks
- `NoDirective(reason=...)`: the input is not asking for a directive
- `UnknownDirective(reason=...)`: the input appears directive-related or interpretation failed, but the drafter should not guess

The `source` field records only the final producer of the returned drafting
result, such as `heuristic` or the source metadata configured for a
host-provided fallback acquisition callback.
It does not track fallback history.

A returned `CanonicalDirective` means "this is a proposed canonical directive,"
not "this directive is permitted" and not "this directive has been applied."

## Recommended Host Flow

1. Run `DirectiveDrafter().draft_directive(message)` as the high-level drafting API. It always tries heuristic drafting first and may optionally call a non-authoritative fallback acquisition callback when the heuristic result is not directly returnable.
2. If you configure a fallback, have it return canonical directive text or `None`, and register the source metadata you want preserved on any fallback-produced `DraftResult`.
3. If the result yields a `CanonicalDirective`, pass that canonical directive to
   `context-compiler` for authoritative review and application.
4. If the result yields `NoDirective`, continue the host flow without a
   directive handoff.
5. If the result yields `UnknownDirective`, preserve the boundary: ask for
   clarification, show resubmission guidance, or retry drafting in a safer
   workflow.

The public helpers remain available unchanged for hosts that prefer to orchestrate heuristic acquisition and fallback candidate validation themselves.

**Safety Guidance:**

- Always validate drafting output before compiler handoff.
- Never pass raw model output directly to the compiler.
- Bypass drafting when clarification is pending.
- Do not drive authoritative transitions from package-owned drafting code.
- Do not read or mutate `engine.state` directly from package-owned drafting code.
- Prefer abstaining over unsafe guesses.
- Output validation checks the canonical directive contract, not whether the
  directive is allowed in context.
- A structurally valid drafted directive may still be the wrong interpretation of the user's meaning.
- Reviewed semantic drafting belongs in a separate higher-level workflow such as preview, approval, or engine application.

Hosts may use `UnknownDirective` to trigger clarification, confirmation, or
resubmission guidance. That interaction is part of the human-input drafting
boundary, but any eventual canonical directive must still be revalidated before
compiler handoff.

Do not pass raw model output to the compiler.

## Prompt Resources

The package includes one shared static converter system prompt for integrations
that use model-based drafting when heuristic drafting does not produce a
result.

Use `get_converter_prompt()` to load the canonical shared converter system prompt.

The converter prompt is guidance only:

- it teaches the basic directive grammar and drafting boundary
- it does not inject premise, policy, engine, or user-specific runtime state
- it does not approve or apply directives
- it does not replace package parsing or validation
- its `<NO_DIRECTIVE>` token is part of the LLM/provider prompt protocol, not a
  `DraftResult` variant and not a Context Compiler grammar rule

If you wire that model call into `DirectiveDrafter`, reuse the shared
converter prompt, configure the fallback callback with source metadata, and
return only candidate directive text or `None`. `DirectiveDrafter` performs
parsing, validation, normalization, and `DraftResult` construction itself.

Heuristic results already carry the parsed `CanonicalDirective` object on success.
Any fallback or model-produced candidate output should still be validated with
`parse_preprocessor_output(...)` or `validate_preprocessor_output(...)` before
it is shown or used.

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

It returns a non-zero exit status because the public high-level drafting API requires a host-provided engine context.

## Development

Run local checks:

```bash
uv run pre-commit run --all-files
uv run pytest
```

## License

Apache-2.0
