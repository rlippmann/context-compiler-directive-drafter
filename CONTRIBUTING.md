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
- decide whether a canonical directive is allowed
- own or redefine directive semantics that belong to the compiler contract

Authoritative state transitions are expected to live in `context-compiler` and
host-controlled orchestration layers.

This package does own the human-input drafting boundary. Documentation and
specification changes in this repository should treat the drafter as responsible
for converting messy user input into one of three non-authoritative outcomes:

- `directive`: propose one canonical directive string
- `no_directive`: classify the message as not requesting a directive
- `unknown`: preserve uncertainty, malformed recovery failure, or unresolved
  directive-like intent without guessing

The authoritative acquisition contract lives in [docs/DrafterAcquisitionSpec.md](docs/DrafterAcquisitionSpec.md).

Use that specification for drafting rules, interpretation-confirmation requirements, clarification-or-resubmission ownership, and migration notes.

Interpretation context is read-only and non-authoritative. It may help the drafter understand phrases like "change it", "remove the old rule", or "use Linux instead of Windows" when current context matters, but it must not turn this package into a second authority layer. The drafter may interpret and propose; only `context-compiler` may validate against authoritative state, authorize operations, and apply resulting directives.

That boundary does not authorize this repository to duplicate the compiler's normative grammar. When an extracted grammar contract is available, this package should reference and consume that contract instead of restating grammar rules as if they were drafter-owned.

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
