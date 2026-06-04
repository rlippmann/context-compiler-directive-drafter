# Context Compiler Directive Drafter

Draft candidate Context Compiler directives from natural-language input.

This package is a drafting layer. Its outputs are non-authoritative.

`context-compiler-directive-drafter` can suggest candidate directives that a
host may present, inspect, or route for further handling. It does not apply
directives, mutate authoritative state, or replace `context-compiler`.

Only `context-compiler` applies directives and mutates authoritative state.

## What this package is for

Natural-language user requests are often close to a directive without being in
the exact canonical form expected by deterministic state machinery.

This package is intended to help hosts:

- draft candidate directives from natural-language input
- keep drafting separate from authoritative state mutation
- make it explicit when output is only a suggestion
- preserve a clear handoff to `context-compiler`

## What this package is not for

This package does not:

- mutate authoritative compiler state
- apply directives directly
- override `context-compiler` decision rules
- silently convert uncertain natural language into authoritative changes

The model or drafting layer may propose. Only `context-compiler` may apply.

## Status

This repository contains the copied experimental directive-drafting
implementation that previously lived alongside `context-compiler`.

The current public package surface is intentionally narrow:

- copied preprocessor API at `context_compiler_directive_drafter`
- packaged prompt resources for installed integrations
- integration examples and tests that preserve the current drafting behavior

Drafting remains non-authoritative. Only `context-compiler` applies validated
directives and mutates authoritative state.

## Quickstart

Install dependencies with `uv`:

```bash
uv sync --group dev
```

Run the current CLI placeholder:

```bash
uv run directive-drafter "please make replies concise"
```

Current CLI behavior still returns a non-zero exit status and explains that
general natural-language drafting flow is not yet exposed as a broader
user-facing command workflow.

## Development

Run the local checks:

```bash
uv run pre-commit run --all-files
uv run pytest
```

## Documentation philosophy

This repository follows the same documentation philosophy as
`context-compiler`:

- explain user-visible behavior before architecture in README-style docs
- keep specification and contract language precise where guarantees matter
- treat examples and tests as part of the project contract when they describe
  intended behavior

## Testing philosophy

This repository follows the same testing philosophy as `context-compiler`:

- favor fast, focused tests over broad but vague coverage claims
- add or update tests for user-facing behavior changes
- keep drafting behavior explicit, inspectable, and contract-driven
- do not weaken tests to accommodate ambiguous implementation shortcuts

## License

Apache-2.0
