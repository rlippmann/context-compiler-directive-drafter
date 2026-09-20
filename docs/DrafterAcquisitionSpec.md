# Directive Drafter Acquisition Specification

## 1. Purpose and authority boundary

This specification defines the acquisition step before Context Compiler
execution. It covers human-facing interpretation that is outside the Core
grammar and state-transition contract.

Each `draft_directive(...)` or `async_draft_directive(...)` call returns a
`DraftResult`. `DraftResult.result` is one of `CanonicalDirective`,
`RejectedDirective`, or `UnknownDirective`. The Drafter is not authoritative:
it must not mutate compiler state or replace Core validation.

The host controls confirmation and submission. Context Compiler remains the
authority for canonical grammar, directive validity, policy decisions,
contradictions, lifecycle rules, state transitions, and execution.

Because a draft is only a proposal, acquisition does not need the confidence
required for an authoritative state change. The Drafter may propose a plausible
single candidate when the user's meaning is naturally represented in compiler
state. It must not guess, create compound proposals, or bypass host approval.

## 2. Input unit and output contract

The Drafter accepts one sentence or one directive request as one acquisition
unit. It does not split a host message into multiple sentences and never emits
multiple candidates. Obvious multi-sentence input is rejected; a host may
segment the message and submit each unit separately.

Each call returns a `DraftResult` with one of these `result` variants:

- `CanonicalDirective`: one proposed canonical directive for host review;
- `RejectedDirective`: a terminal result that must not be sent to fallback;
- `UnknownDirective`: an uncertain result that may be sent to fallback.

`RejectedDirective` uses only these host-actionable reasons:
`non_directive`, `incomplete`, `multiple_directives`, and
`invalid_candidate`. Heuristic implementation details are not part of the
public result contract.

`UnknownDirective` is reserved for an eligible single acquisition unit that is
directive-adjacent but cannot be confidently reduced to one candidate and
cannot be confidently classified as non-directive. It may be sent to fallback.
Multi-sentence, rejected, or terminally malformed input must not reach fallback
through this boundary.

The Drafter must not:

- emit more than one canonical directive for one input;
- synthesize compound state changes;
- bypass Core validation;
- mutate authoritative state.

## 3. Acquisition paths

### Heuristic path

The heuristic path uses deterministic, bounded recognition and rewrite rules.
Failure to recognize canonical syntax or a bounded rewrite is not, by itself,
grounds for rejection. The heuristic path may apply a documented bounded
rewrite when it reduces the full input to one canonical directive without
changing the meaning.

The verified deterministic preference rule is the whole-message form `I prefer
X`, described below. Other policy and premise interpretations are semantic
guidance for optional fallback acquisition, not guarantees of heuristic output.

### Semantic fallback

Semantic fallback is optional interpretation for eligible inputs left unresolved
by the heuristic path. It may be model-based or implemented another way. When
fallback interprets uncertain input, it should prefer `use` or `prohibit`
when that preserves a user-owned preference, requirement, constraint, or
equipment meaning. Premise is residual governing context: use `set premise`
when representing the input as policy would distort its meaning. Do not turn
third-party statements or external facts into the user's policy. Preserve
explicit qualifiers, polarity, and scope.

For fallback evaluation, policy-first examples include:

```text
I have a Nord Stage 4
-> use a Nord Stage 4

We need a simple recipe
-> use a simple recipe

I need oat milk today
-> use oat milk today

I want bamboo towels
-> use bamboo towels

I would rather avoid shellfish
-> prohibit shellfish
```

For fallback evaluation, premise-residual examples include:

```text
The intended audience is senior management
-> set premise intended audience is senior management

User is a minor
-> set premise user is a minor

We need HIPAA compliance
-> set premise need HIPAA compliance

The deployment environment is offline
-> set premise deployment environment is offline
```

Bare facts, observations, evaluations, external rules, and third-party
conditions do not determine their outcome from grammar alone. They may produce
`UnknownDirective` so fallback can interpret their semantic role. A fallback may
propose `use`, `prohibit`, or `set premise` when that preserves the meaning, or
abstain by returning `None` when no interpretation is justified.

The Drafter must not turn third-party statements into the user's policy, resolve
tentative language by guessing, or reduce mixed, malformed, incomplete, or
multiple-directive input to one candidate.

### Explicit preference form

The complete whole-message form `I prefer X` is a bounded deterministic alias
for `use X`:

```text
I prefer concise replies
-> use concise replies
```

This applies only when the full acquisition unit reduces to one canonical
`use` directive. Questions, explanations, empty payloads, and multiple
preference statements do not produce this canonical result.

## 4. Rejection and uncertainty

Rejection is terminal. It covers confidently ordinary input as well as
questions, quoted or reported commands, incomplete directives, and compound or
malformed directive-shaped input.

Unknown preserves uncertainty when the Drafter cannot confidently produce one
candidate and cannot confidently classify the input as non-directive. Only
Unknown is eligible for fallback.

The Drafter should abstain rather than guess when more than one canonical
directive is plausible. It should also preserve the ownership boundary when
input is tentative, third-party, mixed, malformed, or incomplete.

## 5. Narrowing rules

The deterministic path may narrow input only through a documented bounded rule.
It:

- may apply a specifically authorized rule to produce one atomic candidate;
- must not add mutations or silently select a different operation;
- must preserve payload, polarity, and scope by default, including temporal and
  situational qualifiers;
- must not paraphrase, substitute synonyms, generalize scope, invent
  alternatives, or change semantic nouns;
- must leave contradiction and lifecycle validation to Core.

### Near-miss canonical forms

These acquisition patterns interpret existing Core grammar; they do not add
new Core grammar productions:

- `set premise to X` -> `set premise X`;
- `change premise X` -> `change premise to X`.

`X` must be non-empty after the near-miss prefix. If the apparent intent cannot
be preserved, it produces `RejectedDirective` or `UnknownDirective` according
to the existing heuristic classification. The host may ask for clarification
after receiving `UnknownDirective`.

Canonical replacement syntax, such as `use X instead of Y`, belongs to Core's
grammar and application semantics. This API does not inspect authoritative
policy state or reinterpret a missing source item. Any future context-assisted
acquisition would require a separate API and contract.

## 6. Host responsibilities

The host is responsible for:

- segmenting obvious multi-sentence conversational input when that workflow is
  desired;
- deciding whether confirmation is required;
- deciding whether to submit a candidate to Core;
- managing clarification, resubmission, and other user-facing interaction.

For non-canonical input, the Drafter returns one of the three public results: a
`CanonicalDirective`, a terminal `RejectedDirective`, or an `UnknownDirective`.
After `UnknownDirective`, the host may ask for clarification, invoke an
optional fallback, or treat the input as unresolved. This specification does
not require one fixed prompt or confirmation workflow.

## 7. Explicit non-goals and prohibited behavior

The Drafter does not own:

- conversational sentence segmentation;
- canonical directive validation;
- authoritative state validation;
- deterministic state transitions;
- contradiction handling after a candidate is chosen;
- directive application or state mutation;
- compiler-owned directive semantics.

The Drafter must not become a second authority layer, silently upgrade
ambiguous language into state changes, emit compound proposals, or bypass the
host and Core workflow.
