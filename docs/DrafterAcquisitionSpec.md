# Directive Drafter - Acquisition Specification

## Goal

Define the acquisition-layer behavior that sits before core execution.

This document covers human-facing interpretation that is intentionally outside
the core authority contract in
[Context Compiler Directive Grammar Specification](https://github.com/rlippmann/context-compiler/blob/main/docs/DirectiveGrammarSpec.md).

The drafter is non-authoritative: it may propose canonical directives for core,
but it does not mutate authoritative state and does not replace core
validation.

The host application owns any confirmation workflow before submitting a drafted
directive to core.

## 1. Ownership Boundary

The drafter owns:

- near misses of canonical directives
- alternate human phrasing
- malformed-but-recoverable input
- deciding when a candidate directive, clarification, or no-directive result
  is appropriate for non-canonical input
- context-assisted interpretation before core execution
- proposed semantic narrowing from non-canonical input to one canonical
  directive candidate

The drafter does not own:

- authoritative state mutation
- canonical directive validation
- authoritative state validation
- deterministic state transitions
- contradiction handling after a canonical directive is chosen
- core-owned validation or execution after a canonical directive is submitted

Core remains the authority for those behaviors in the
[Context Compiler Directive Grammar Specification](https://github.com/rlippmann/context-compiler/blob/main/docs/DirectiveGrammarSpec.md).

## 2. Drafter Output Contract

The drafter may return one of these outcomes to the host:

- a single canonical directive candidate to submit to core
- a request for clarification
- no directive, leaving the input as ordinary non-directive text

A drafted directive is a proposal only.

The host application is responsible for:

- deciding whether confirmation is required;
- deciding whether to submit the candidate to core;
- managing user-facing interaction.

The drafter must not:

- emit more than one canonical directive for a single user input
- synthesize compound state changes from one user input
- bypass core validation
- mutate authoritative state directly

## 3. Proposed Narrowing Rules

When narrowing non-canonical input into one canonical directive candidate, the
drafter:

- may preserve one apparent atomic user mutation
- may propose a narrower canonical directive
- must not add extra mutations beyond that atomic change
- must not silently replace user intent with a different operation
- must abstain when more than one canonical directive is plausible
- must leave contradiction and lifecycle validation to core after drafting

These rules preserve the authority split:

- drafter interprets and proposes
- host controls submission workflow
- core validates and executes

## 4. Near-Miss Canonical Forms

These behaviors belong to acquisition because they interpret user input into
existing core grammar.

Supported near-miss patterns:

- `set premise to X`
  - candidate canonical directive:
    `set premise X`

- `change premise X`
  - candidate canonical directive:
    `change premise to X`

Constraints:

- the payload `X` must be non-empty after the near-miss prefix
- these are drafting behaviors, not additional core grammar productions
- the drafter must not submit unrelated mutations
- if the drafter cannot preserve the user's apparent intent, it should ask
  for clarification or return no directive

## 5. Replacement Interpretation

Replacement interpretation belongs to acquisition when the submitted input
cannot be executed literally by core and would need reinterpretation.

### 5.1 Missing-source replacement

Example:

```text
use Linux instead of Windows
```

If `Windows` is not present in authoritative policy state, core does not repair
this into a different directive.

A drafter may use context to propose a candidate canonical directive such as:

```text
use Linux
```

Proposed narrowing constraints:

- the result must remain a single atomic mutation
- the result must not imply removal of another item
- the drafter must not silently emit additional mutations
- the host decides whether confirmation is required before submission

Allowed flow:

1. User input: `use Linux instead of Windows`
2. Context indicates `Windows` is not currently present
3. Drafter proposes: `use Linux`
4. Host workflow decides whether to submit the candidate
5. Host submits canonical directive `use Linux` to core

Not allowed:

1. User input: `use Linux instead of Windows`
2. Context indicates `Windows` is not currently present
3. Drafter silently submits `use Linux` to core

### 5.2 Prohibited-item replacement interpretations

Historical core prompts also covered cases like:

- `"Y" is currently prohibited. Did you mean to remove it and use "X" instead?`
- `"X" is currently prohibited. Did you mean to remove "Y" and use "X" instead?`

Those interpretations are acquisition-layer behaviors because they rewrite the
submitted replacement request into materially different policy operations.

Current ownership:

- drafter may decide whether to propose a candidate, request clarification,
  or return no directive
- core must not authorize rewritten mutations from the original non-canonical
  input

## 6. Clarification and Resubmission

For non-canonical input, the drafter may:

- suggest a canonical rewrite
- suggest a narrower canonical directive candidate
- ask the user for clarification
- return no directive and treat the message as ordinary conversation

This document does not require one fixed user-facing prompt set for all
acquisition behaviors.

The user-facing interaction remains host-defined unless another host-owned
document standardizes it.

## 7. Context-Assisted Interpretation

The drafter may use host context to interpret non-canonical user input before
core execution.

Allowed uses:

- choosing between a candidate directive and no directive
- deciding whether a simpler single canonical proposal preserves intent
- deciding when clarification is needed

Not allowed:

- silently committing authoritative state changes
- silently submitting a narrowed canonical directive without host workflow
- using context to create compound mutations from one input
- overriding core contradiction or lifecycle rules

## 8. Migration Table

| Previous behavior in core grammar spec | New owner | New document section |
| --- | --- | --- |
| Canonical syntax and state-transition semantics for directives | Core grammar contract | Context Compiler Directive Grammar Specification |
| Premise near-miss `set premise to X` -> candidate `set premise X` | Drafter acquisition layer | Sections 3 and 4 |
| Premise near-miss `change premise X` -> candidate `change premise to X` | Drafter acquisition layer | Sections 3 and 4 |
| Replacement missing-source narrowing from `use X instead of Y` to candidate `use X` | Drafter acquisition layer | Sections 3 and 5.1 |
| Replacement rewrite when old item is prohibited | Drafter acquisition layer | Section 5.2 |
| Replacement rewrite when new item is prohibited | Drafter acquisition layer | Section 5.2 |
| Clarification or no-directive result for ambiguous or non-recoverable input | Drafter acquisition layer | Section 6 |
| Context-assisted narrowing from non-canonical input to one canonical directive candidate | Drafter acquisition layer | Sections 3 and 7 |

## 9. Migration Notes

The intended ownership boundary is:

```text
user input
    |
    v
Drafter acquisition layer
    |
    v
candidate canonical directive or no directive
    |
    v
host workflow
    |
    v
core validation and execution
```

Legacy acquisition behavior may still exist in implementations or fixtures, but
those behaviors are not part of the core grammar contract.

Core owns:

- canonical syntax;
- directive classification;
- syntax validation;
- state transitions.

Drafter owns:

- human-facing acquisition;
- non-canonical phrasing;
- candidate generation;
- clarification decisions.

The host owns:

- confirmation workflow;
- submission decisions;
- user interaction.

## 10. Design Questions

These design questions remain open and are intentionally not resolved here:

- which host confirmation workflows, if any, should be standardized across hosts
- how much host context is sufficient to justify narrowing non-canonical input
  into a simpler canonical directive candidate
- whether any host confirmation workflow should be standardized separately
  from core confirmation
