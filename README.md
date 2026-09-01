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
- Distinguish terminal rejection from semantic uncertainty in a stable
  host-facing contract.
- Avoid accidental candidate drafts from ambiguous input.
- Add a conservative natural-language-to-directive step before applying changes.

This package owns the human-facing acquisition boundary, including exact
canonicalization, bounded deterministic rewrites, obvious non-directive
rejection, and fallback eligibility for semantically uncertain interpretation.
It does not decide whether a drafted candidate is valid, applicable, allowed,
contradictory, or executable; Core owns those decisions.

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
from context_compiler_directive_drafter import RejectedDirective, UnknownDirective

drafter = DirectiveDrafter()

result = drafter.draft_directive(
    "Please use Docker for container examples.",
)

if hasattr(result.result, "text"):
    print("Candidate directive:", result.result.text)
elif isinstance(result.result, RejectedDirective):
    print("Directive acquisition rejected:", result.result.reason)
elif isinstance(result.result, UnknownDirective):
    print("Need clarification before drafting:", result.result.reason)
```

The host validates drafted output before passing a `CanonicalDirective` candidate
to `engine.apply_directive(...)` for authoritative evaluation and application.

For a small runnable example, see [examples/basic_usage.py](examples/basic_usage.py).

## English Evaluation Corpus

The reusable English-language acquisition and fallback evaluation corpus lives
in [`evals/corpus/english/directive-drafter-en.jsonl`](evals/corpus/english/directive-drafter-en.jsonl).
It contains heuristic contracts, fallback evaluation cases, and selected
fixture-backed anchors. The corpus is evaluation data only; existing
conformance fixtures remain the executable compatibility authority. See
[docs/EnglishEvaluationCorpus.md](docs/EnglishEvaluationCorpus.md) for the
schema, classifications, domain scope, and promotion workflow.

## OpenAI-Compatible Fallback

Install the optional integration extra:

```bash
pip install "context-compiler-directive-drafter[openai]"
```

Use it with OpenAI by creating a fallback callback and passing it to the
Drafter:

```python
import os

from context_compiler_directive_drafter import DirectiveDrafter
from context_compiler_directive_drafter.fallbacks.openai import create_openai_fallback

fallback = create_openai_fallback(
    model="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],
)
drafter = DirectiveDrafter(fallback=fallback, fallback_source="openai")
```

The asynchronous factory performs the same construction-time probe and must
be awaited:

```python
fallback = await create_async_openai_fallback(model="gpt-4o-mini")
```

OpenAI-compatible providers use the same helper with a custom endpoint, for
example an Ollama server:

```python
fallback = create_openai_fallback(
    model="qwen2.5:7b",
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)
```

The helper probes structured-output support once while it is constructed,
then selects the package-owned converter prompt and transport mode for all
callback calls. Structured mode owns the JSON Schema response envelope;
unsupported providers use free-text mode, which translates the provider-level
`<NO_DIRECTIVE>` abstention sentinel to
the generic fallback callback contract's Python `None` value. Other model text
is returned unchanged. The Drafter remains responsible for parsing, validation,
and result shaping.

### Native fallback integrations

Hosts using a provider-specific client can implement the fallback callback
directly while reusing the package-owned acquisition contract:

```python
from context_compiler_directive_drafter.fallbacks import (
    InvalidFallbackResponseError,
    NO_DIRECTIVE,
    get_converter_prompt,
    get_structured_converter_prompt,
    get_structured_output_schema,
)
```

Use `get_converter_prompt()` when the provider returns canonical directive text,
or use `get_structured_converter_prompt()` with
`get_structured_output_schema()` when it supports structured output. Return
`None` for a valid provider rejection, and raise
`InvalidFallbackResponseError` for a malformed or inconsistent structured
response. The callback returns raw candidate text; the Drafter passes it through
Core parsing and produces the non-authoritative result.

### Live English Corpus Runner

The live runner executes selected corpus cases through the real
`DirectiveDrafter` path. Install the optional OpenAI dependency first, then
run a small subset before a larger evaluation:

```bash
# OpenAI, using OPENAI_API_KEY from the environment
uv run python -m evals.runners.directive_drafter_en \
  --model gpt-4o-mini \
  --case-id en-software-preference-001

# Any OpenAI-compatible endpoint
uv run python -m evals.runners.directive_drafter_en \
  --model qwen2.5:7b \
  --api-key ollama \
  --base-url http://localhost:11434/v1 \
  --domain software_development \
  --category preference_statement \
  --limit 3

# Write detailed JSONL records to the ignored eval-results directory
uv run python -m evals.runners.directive_drafter_en \
  --model gpt-4o-mini \
  --limit 10 \
  --output eval-results/sample.jsonl
```

The runner reports totals, heuristic versus fallback routing, domain and
category breakdowns, and failure categories. It does not change the corpus
expectations or act as a conformance authority. JSONL records include the
actual path, path agreement, fallback invocation count, and raw fallback
response; semantic scoring and routing mismatches are reported separately.

### Conformance layers

The checked-in contract fixtures use the existing `pytest.mark.contract` and
fixture model. `high-level-drafting-v1.json` defines shared API concepts and
observable drafting behavior for compatible ports, including the
`DirectiveDrafter`, result variants, fallback routing, source metadata, and
public rejection reasons. `public-api-v1.json` defines Python package
mechanics such as root exports, reflection-visible signatures, descriptors,
and Python exception behavior; those details are not requirements for other
languages.

Heuristic fixture inputs and portable expected outcomes are shared behavior.
Private Python entry points and detailed internal diagnostic reasons are
Python implementation coverage. The English evaluation corpus remains
evaluation-only except for cases explicitly linked to promoted heuristic
fixtures.

## Public API

Public interface:

- `DirectiveDrafter()`: Synchronous orchestration over heuristic preprocessing, optional fallback acquisition, fallback output parsing and validation, and final result construction.
- `DraftResult`: Structured non-authoritative result returned by `DirectiveDrafter.draft_directive(...)`.
- `RejectedDirective` and `UnknownDirective`: Non-canonical drafting result variants with preserved reasons.
- `create_openai_fallback(...)`: Create a synchronous OpenAI-compatible fallback callback.
- `create_async_openai_fallback(...)`: Create an asynchronous OpenAI-compatible fallback callback.
- `context_compiler_directive_drafter.fallbacks`: Public prompt, structured-schema, abstention-sentinel, and invalid-response helpers for native fallback integrations.
- `context_compiler_directive_drafter.fallbacks.openai`: Optional OpenAI-compatible fallback factories.

### Output Contract

The intended drafting boundary is:

- input: user text
- output: `DraftResult(source=<final producer>, result=<drafting-layer variant>)`

Every drafting path should end in one of three host-visible result variants:

- `CanonicalDirective`: a proposed canonical directive that is ready for compiler review and independent policy checks
- `RejectedDirective(reason=...)`: acquisition is terminally rejected and must not reach fallback
- `UnknownDirective(reason=...)`: the input appears directive-related or interpretation failed, but the drafter should not guess

The heuristic uses these outcomes deliberately:

- `RejectedDirective` means acquisition is terminally rejected, including
  ordinary prose, questions, quoted or reported commands, incomplete
  directives, and compound or malformed input. It is never fallback-eligible.
  Its stable public reasons are `non_directive`, `incomplete`,
  `multiple_directives`, and `invalid_candidate`.
- `UnknownDirective` means semantic interpretation remains plausible but the
  heuristic cannot confidently produce one candidate. This result alone is
  eligible for host fallback interpretation.

Failure to recognize canonical syntax or a bounded rewrite is not, by itself,
evidence for `RejectedDirective`.

As a bounded deterministic rewrite, a clear whole-message `I prefer X` form is
treated like `please use X` and produces the proposed candidate `use X` when
the payload reduces to one canonical directive. Questions, mixed explanations,
and multiple preference statements remain unresolved. This does not apply to
general evaluative language such as `Docker would be better`.

The `source` field records only the final producer of the returned drafting
result, such as `heuristic` or the source metadata configured for a
host-provided fallback acquisition callback.
It does not track fallback history.

A returned `CanonicalDirective` means "this is a proposed canonical directive,"
not "this directive is permitted" and not "this directive has been applied."

## Recommended Host Flow

1. Run `DirectiveDrafter().draft_directive(message)` as the high-level drafting API. It always tries heuristic drafting first and may optionally call a non-authoritative fallback acquisition callback when the heuristic returns `UnknownDirective`.
2. If you configure a fallback, have it return canonical directive text or `None`, and register the source metadata you want preserved on any fallback-produced `DraftResult`.
3. If the result yields a `CanonicalDirective`, pass that canonical directive to
   `context-compiler` for authoritative review and application.
4. If the result yields `RejectedDirective`, continue the host flow without a
   directive handoff.
5. If the result yields `UnknownDirective`, preserve the boundary: ask for
   clarification, show resubmission guidance, or retry drafting in a safer
   workflow.

Custom fallback callbacks receive the original user input and return raw text or
`None`. Provider callbacks own provider response parsing; `DirectiveDrafter`
owns candidate normalization, Core validation, and result construction.

**Safety Guidance:**

- Always validate drafting output before compiler handoff.
- Never pass raw model output directly to the compiler.
- Bypass drafting when clarification is pending.
- Do not drive authoritative transitions from package-owned drafting code.
- Do not read or mutate `engine.state` directly from package-owned drafting code.
- Prefer abstaining when the input cannot be confidently reduced to one directive.
- Output validation checks the canonical directive contract, not whether the
  directive is allowed in context.
- A structurally valid drafted directive may still be the wrong interpretation of the user's meaning.
- Reviewed semantic drafting belongs in a separate higher-level workflow such as preview, approval, or engine application.

Hosts may use `UnknownDirective` to trigger clarification, confirmation, or
resubmission guidance. That interaction is part of the human-input drafting
boundary, but any eventual canonical directive must still be revalidated before
compiler handoff.

Do not pass raw model output to the compiler.

## Current Limits

This package is intentionally conservative. It returns `UnknownDirective` only
when a single acquisition unit is directive-adjacent but remains semantically
uncertain:

- The input may be ambiguous or not safely interpretable as one canonical
  directive.
- The input may be embedded in prose, markdown, or code when the heuristic
  cannot establish a terminal non-directive boundary.

Boundary rules:

- Process the full message, not fragments.
- Treat one sentence or one directive request as the acquisition unit. The
  drafter does not perform conversational sentence segmentation.
- Emit at most one canonical directive.
- Reject when one message contains multiple directive-shaped instructions.
- Do not mine surrounding prose for commands.
- Do not split one message into multiple drafted directives.
- Do not invent new directive semantics.
- Apply only bounded deterministic rewrites that preserve one apparent
  directive operation.
- Defer ambiguous semantic interpretation to the host fallback when available.

Obvious multi-sentence conversational input is outside the acquisition unit.
The heuristic returns `rejected` for that input rather than sending it to
fallback. The host is responsible for sentence segmentation and may resubmit
the resulting units individually. `unknown` is reserved for an eligible
single acquisition unit that is directive-adjacent but cannot be confidently
reduced to one canonical candidate and may require fallback. Core remains
responsible for canonical directive validity, applicability, authorization,
and execution; it does not own host sentence segmentation.

Questions are terminal acquisition rejections. Forms such as `allow docker?`,
`do not use peanuts?`, `please use docker?`, and `can you help with lunch?`
return `rejected`; they never reach fallback or become heuristic candidates.

Quoting is intentionally distinct from quoting an operand: a full-message
command such as `"use docker"` is treated as quoted or reported text and is
terminally rejected, while `use "docker"` is a canonical `use` candidate whose
operand is the literal quoted text. The heuristic does not strip operand quotes.

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
