# AGENTS.md

Guidelines for AI agents working in this repository.

## Branch rules
- Never commit directly to `main`.
- Never push directly to `main`.
- Never check out or modify `main`.
- Always work on a feature branch.
- If the current branch is `main`, stop and ask the user to create a branch.

## Development workflow
Before committing:
1. Run `uv run pre-commit run --all-files`
2. Run `uv run pytest`

Do not bypass pre-commit hooks.

## Repository boundary

This package drafts candidate Context Compiler directives from natural-language input.

Drafts are non-authoritative.

Only `context-compiler` applies directives and mutates authoritative state.

Do not describe drafting as:
- validation authority
- directive authority
- state mutation
- authoritative application

Be explicit that drafting proposes and `context-compiler` decides.

## Context Compiler integration rules

- Do not bypass `engine.step(...)`.
- Do not edit `engine.state`.
- Do not introduce flows that mutate authoritative state outside `context-compiler`.
- Do not describe candidate drafting output as equivalent to an engine decision.
- Keep the handoff boundary explicit between drafting output and compiler-owned application.
- Keep `src/context_compiler_directive_drafter/**` and package-owned `examples/**` compatible with `scripts/check_boundaries.py` by avoiding direct `create_engine(...)`, `engine.step(...)`, `engine.state`, `.state =`, and runnable host-integration imports there.

## Public API and imports

- The public import package is `context_compiler_directive_drafter`.
- The CLI command is `directive-drafter`.
- Do not preserve or reintroduce legacy `context_compiler_directive_drafter` imports.
- Do not add compatibility aliases that blur the public package boundary unless explicitly requested.

## Test coverage expectations
Before opening a PR, consider:

* Does this change affect any user-facing drafting behavior?
* If so, is that behavior covered by tests?

User-facing behavior includes:

* candidate directive outputs
* abstention behavior
* validation behavior
* prompt and resource loading
* CLI exit status and output contract
* replay-input-only preprocessing behavior in integration examples
* forwarded-message preservation in integration examples
* integration handoff boundaries between the drafter and `context-compiler`

If a user-facing behavior is changed or introduced, add or update tests to cover it.

Do not weaken tests to make extraction easier.
Do not rely solely on coverage metrics.

## Scope of changes
- Only modify files necessary for the requested task.
- Do not refactor unrelated code.
- Do not change project structure unless explicitly asked.
- Make the minimal change required to solve the requested task.
- If the task expands beyond the original request, stop and ask the user for guidance.

## Dependencies
If tests fail due to missing dependencies, install them rather than skipping tests.

## Python version
This project targets modern Python (3.11+).

Do not add compatibility code for older Python versions.

Avoid constructs that were only required for older Python versions, including:
- `from __future__ import annotations`
- `typing_extensions` replacements for stdlib features
- version guards like `if sys.version_info < ...`

Prefer modern typing syntax:
- `list[str]` instead of `List[str]`
- `dict[str, int]` instead of `Dict[str, int]`
- `str | None` instead of `Optional[str]`

## Git safety
- Do not perform history-rewriting operations unless explicitly instructed.
- This includes `git rebase`, `git reset`, `git push --force`, and `git commit --amend`.
- Do not push directly to `main`.
- Do not check out or modify `main`.
- If the current branch is `main`, stop and ask the user to create a feature branch.

## Commit messages
- Commit messages must use this format: `<type>: <summary>`.
- The `<type>` token must be lowercase letters only.
- The `<summary>` must be short and written in imperative mood.
- Allowed `<type>` values: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.
- If a proposed commit message does not match this format or type list, stop and ask for a corrected message before committing.

## PR guidance
- Never open or merge a PR targeting `main` from `main`; always use a feature branch.
- Always use the repository PR template when creating or updating PR descriptions.
- PR titles must use the same format as commits: `<type>: <summary>`.
- PR descriptions should include:
  - what changed
  - why the change was needed
- Do not include a dedicated "Validation" section in PR text.
- Keep PR scope aligned to the requested task; if scope grows, ask for guidance before expanding.

## Issue guidance
- Always use the repository issue templates when creating or updating issues.
- Use `bug_report` for defects and regressions.
- Use `feature_request` for new capabilities or enhancements.

## CI
Do not modify GitHub CI workflows unless explicitly asked.

## Documentation
Specification documents are authoritative.

Do not change specification documents unless explicitly instructed.

If implementation behavior does not match the specification, report the mismatch instead of modifying the specification.

Documentation is not commentary.

This repository is the canonical documentation owner for
`context-compiler-directive-drafter`.

Package-level drafting documentation should live here, not in
`context-compiler`.

Keep the ownership boundary explicit:
- `context-compiler-directive-drafter` owns drafting-package docs, prompt/resource usage docs, and drafting integration guidance for this package
- `context-compiler` owns compiler behavior, engine semantics, authoritative state mutation, and directive application rules

README examples, integration examples, migration guides, CLI usage
documentation, and explicitly requested documentation changes are part of the
project contract.

Treat documentation requirements in a task as acceptance criteria.

Treat user-visible documentation as a behavioral contract, not as optional narrative.

Do not treat documentation as illustrative unless explicitly stated.
Do not silently change documented behavior because implementation is easier.
Do not update documentation merely to match unintended behavior.
Do not weaken or remove user-facing tests to accommodate implementation.

Documentation examples explicitly referenced by a task are part of the
expected deliverable.

If implementation, documentation, examples, tests, fixtures, and
specifications disagree:

1. Specifications and fixtures are authoritative.
2. Report the mismatch.
3. Request review before changing documented behavior.
4. Do not resolve disagreements by silently changing docs.

Drift detection is required work, not optional polish.

When changing behavior or docs, actively check for drift across:
- README contract language
- integration examples and their documented behavior
- CLI usage and exit/output descriptions
- prompt/resource loading behavior
- exported package surface and package-listing claims
- tests, fixtures, and captured examples

If you find drift:
- report it clearly
- fix the contract or implementation only in the canonically owned location
- do not preserve duplicate or conflicting wording across files
- do not move core-owned compiler docs into this repository unless explicitly instructed

## Documentation style

For README, integration, migration, CLI, and package-listing docs, explain
user-visible drafting behavior before architecture.

Lead with what the package does, how users or hosts use it, and how it relates
to `context-compiler` before discussing implementation structure or project
history.

Be explicit that drafting proposes and `context-compiler` decides.

Prefer plain, concrete wording when accurate. Examples:
- "draft candidate directives"
- "non-authoritative suggestion"
- "saved authoritative state"
- "only the compiler may apply"
- "drafting proposes and the compiler decides"

Avoid describing drafting as:
- validation authority
- state mutation
- authoritative application
- a replacement for `context-compiler`
- the owner of compiler decisions
- an "experimental preprocessor" when referring to the current public package surface unless the task explicitly requires historical terminology

Avoid describing features only in architectural terms when a behavior-first explanation is possible.

Avoid architecture-archeology framing in README-style docs when present-tense
ownership and behavior are what users need.

Prefer direct subjects and strong verbs.
Avoid noun stacks and passive phrasing when a simpler active sentence is clearer.
Use simpler wording unless technical precision requires formal terminology.

Specification and contract documents are different:
- preserve precise terminology
- preserve unambiguous behavioral guarantees
- do not weaken formal semantics for readability

Do not simplify contract or specification wording in ways that blur required
behavior, ownership boundaries, or authoritative semantics.

Do not rewrite captured outputs, fixture-sensitive examples, or eval evidence unless explicitly asked.

## Tooling
Use the project's existing tooling:

- Run commands via `uv run` when appropriate.
- Development dependencies are installed with `uv sync --group dev`.
