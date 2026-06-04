# Contributing

Thanks for your interest in improving this project. Contributions are welcome.

## Workflow

Contributions are typically submitted via fork and pull request:

- fork the repository
- create a feature branch
- run tests and pre-commit checks
- open a pull request

## Development Setup

```bash
uv sync --group dev
```

## Running Tests

```bash
uv run pytest
```

## Code Quality

```bash
uv run pre-commit run --all-files
```

## Scope of Changes

- keep pull requests focused
- include tests if behavior changes
- open an issue first for large design changes

## Architectural Boundaries

The drafting boundary is intentional.

This package may draft candidate directives from natural-language input, but it
is not an authoritative state engine. It is not designed to:

- mutate live compiler state
- replace `context-compiler`
- silently upgrade ambiguous language into authoritative changes
- blur the distinction between proposal and application

Authoritative state transitions are expected to live in `context-compiler` and
host-controlled orchestration layers.

Changes that weaken that separation should be treated as architectural
proposals, not routine feature requests.

## Documentation Style

For README, CLI, and package-listing docs, explain user-visible behavior before
architecture.

Prefer plain, concrete wording when accurate. For example:
- "draft candidate directives"
- "non-authoritative suggestion"
- "saved authoritative state"
- "only the compiler may apply"

Avoid describing features only in architectural terms when a behavior-first
explanation is possible.

Specification and contract documents are different: preserve precise
terminology and unambiguous behavioral guarantees. Do not simplify formal docs
in ways that weaken guarantees or change meaning.
