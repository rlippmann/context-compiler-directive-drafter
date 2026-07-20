# Directive Drafter - Acquisition Specification

## Goal

Define the acquisition-layer behavior that sits before core execution.

This document covers human-facing interpretation that is intentionally outside
the core authority contract in
[Context Compiler Directive Grammar Specification](https://github.com/rlippmann/context-compiler/blob/main/docs/DirectiveGrammarSpec.md).
The drafter is non-authoritative: it may propose canonical directives for core,
but it does not mutate authoritative state and does not replace core
validation.

Interpretation confirmation in this document means confirming a drafter-proposed
meaning before any canonical directive is submitted to core. Core confirmation
refers to core-owned confirmation of a known canonical state transition after a
canonical directive has already been submitted.

## 1. Ownership Boundary

The drafter owns:

- near misses of canonical directives
- alternate human phrasing
- malformed-but-recoverable input
- deciding when clarification or resubmission is needed for non-canonical
  input, while host UX remains host-defined
- context-assisted interpretation before core execution
- proposed semantic narrowing from non-canonical input to one canonical
  directive, with explicit user confirmation before submission to core

The drafter does not own:

- authoritative state mutation
- canonical directive validation
- authoritative state validation
- deterministic state transitions
- contradiction handling after a canonical directive is chosen
- core-owned canonical or mutation confirmation after a canonical directive is
  submitted

Core remains the authority for those behaviors in the
[Context Compiler Directive Grammar Specification](https://github.com/rlippmann/context-compiler/blob/main/docs/DirectiveGrammarSpec.md).

## 2. Drafter Output Contract

The drafter may return one of these outcomes to the host:

- a single canonical directive to submit to core
- a proposed canonical directive that requires explicit interpretation
  confirmation before submission to core
- a request for clarification or resubmission from the user
- abstention, leaving the input as ordinary non-directive text

The drafter must not:

- emit more than one canonical directive for a single user input
- synthesize compound state changes from one user input
- bypass `engine.step(...)`
- mutate authoritative state directly

## 3. Proposed Narrowing Rules

When narrowing non-canonical input into one canonical directive, the drafter:

- may preserve one apparent atomic user mutation
- may propose a narrower canonical directive
- must not add extra mutations beyond that atomic change
- must not turn one failed replacement request into multiple policy updates
- must not silently replace user intent with a different operation
- must obtain explicit user interpretation confirmation before a narrowed
  directive becomes a canonical directive submitted to core
- must abstain when more than one canonical directive is plausible
- must leave contradiction and lifecycle validation to core after drafting

These rules preserve the authority split:

- drafter interprets
- core validates and executes

## 4. Near-Miss Canonical Forms

These behaviors were previously documented inside the core grammar spec and now
belong to acquisition.

Supported near-miss patterns:

- `set premise to X`
  - proposed canonical directive after interpretation confirmation:
    `set premise X`
- `change premise X`
  - proposed canonical directive after interpretation confirmation:
    `change premise to X`

Constraints:

- the payload `X` must be non-empty after the near-miss prefix
- these are drafting behaviors, not additional core grammar productions
- the drafter must not submit the narrowed canonical directive to core without
  explicit user interpretation confirmation
- if the drafter cannot preserve the user’s apparent premise update exactly, it
  should ask for clarification or resubmission instead of guessing

## 5. Replacement Interpretation

Replacement interpretation belongs to acquisition when the submitted input
cannot be executed literally by core and would need reinterpretation.

### 5.1 Missing-source replacement

Example:

```text
use Linux instead of Windows
```

If `Windows` is not present in authoritative policy state, core does not repair
this into a different directive. A drafter may use context to propose a
canonical directive such as:

```text
use Linux
```

Only after explicit user interpretation confirmation may that canonical
directive be submitted to core.

Proposed narrowing constraints:

- the result must remain a single atomic mutation
- the result must not imply removal of another item
- the drafter must not silently emit the narrowed directive
- if the host lacks enough context to justify narrowing safely, the drafter
  should ask the user for clarification or resubmission

Allowed flow:

1. User input: `use Linux instead of Windows`
2. Context indicates `Windows` is not currently present
3. Drafter proposes: `use Linux`
4. User provides interpretation confirmation
5. Host submits canonical directive `use Linux` to core

Not allowed:

1. User input: `use Linux instead of Windows`
2. Context indicates `Windows` is not currently present
3. Drafter silently emits `use Linux` to core

### 5.2 Prohibited-item replacement interpretations

Historical core prompts also covered cases like:

- `"Y" is currently prohibited. Did you mean to remove it and use "X" instead?`
- `"X" is currently prohibited. Did you mean to remove "Y" and use "X" instead?`

Those interpretations are acquisition-layer behaviors because they rewrite the
submitted replacement request into materially different policy operations.

Current ownership:

- drafter may decide whether to ask for clarification, resubmission, or an
  interpretation-confirmed narrowing proposal
- core must not authorize those rewritten mutations from the original
  non-canonical input

## 6. Clarification and Resubmission

For non-canonical input, the drafter may:

- suggest a canonical rewrite
- suggest a narrower canonical directive that still requires explicit
  interpretation confirmation
- ask the user to resubmit using a canonical directive
- abstain and treat the message as ordinary conversation

This document does not require one fixed user-facing prompt set for all
acquisition behaviors. The drafter decides when clarification or resubmission
is needed; the user-facing interaction remains host-defined unless another
host-owned document standardizes it.

## 7. Context-Assisted Interpretation

The drafter may use host context to interpret non-canonical user input before
core execution.

Allowed uses:

- choosing between a near-miss form and plain conversation
- deciding whether a failed replacement request is better treated as a simpler
  single canonical directive proposal
- deciding when to abstain and ask for clarification

Not allowed:

- silently committing authoritative state changes without core
- silently submitting a narrowed canonical directive to core without explicit
  user interpretation confirmation
- using context to create compound mutations from one input
- overriding core contradiction or lifecycle rules

## 8. Migration Table

| Previous behavior in core grammar spec | New owner | New document section |
| --- | --- | --- |
| Canonical syntax and state-transition semantics for directives | Core grammar contract | Context Compiler Directive Grammar Specification |
| Premise near-miss `set premise to X` -> propose `set premise X` with interpretation confirmation | Drafter acquisition layer | Sections 3 and 4 |
| Premise near-miss `change premise X` -> propose `change premise to X` with interpretation confirmation | Drafter acquisition layer | Sections 3 and 4 |
| Replacement missing-source narrowing from `use X instead of Y` to `use X` with interpretation confirmation | Drafter acquisition layer | Sections 3 and 5.1 |
| Replacement rewrite when old item is prohibited | Drafter acquisition layer | Section 5.2 |
| Replacement rewrite when new item is prohibited | Drafter acquisition layer | Section 5.2 |
| Clarification or resubmission for non-canonical but recoverable input | Drafter acquisition layer | Section 6 |
| Context-assisted narrowing from non-canonical input to one canonical directive proposal | Drafter acquisition layer | Sections 3 and 7 |

## 9. Migration Notes

As of July 20, 2026, the live core implementation still contains some legacy
acquisition behavior:

- premise near-miss repair for `set premise to ...`
- premise near-miss repair for `change premise ...`
- missing-source replacement confirmation that effectively becomes `use X`

Those behaviors remain in implementation and fixtures for now, but they are no
longer part of the intended core contract.

## 10. Design Questions

These design questions remain open and are intentionally not resolved here:

- which interpretation-confirmation prompts, if any, should be standardized
  across hosts
- how much host context is sufficient to justify narrowing a failed replacement
  request into a simpler canonical directive
- whether interpretation confirmation should ever be standardized separately
  from core confirmation
