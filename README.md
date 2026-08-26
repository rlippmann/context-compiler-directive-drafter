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
- Avoid accidental candidate drafts from ambiguous input.
- Add a conservative natural-language-to-directive step before applying changes.

This package owns the human-facing acquisition boundary, including exact
canonicalization, bounded deterministic rewrites, obvious non-directive
rejection, and fallback deferral for ambiguous interpretation. It does not
decide whether a drafted candidate is valid, applicable, allowed, contradictory,
or executable; Core owns those decisions.

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

The host validates drafted output before passing a `CanonicalDirective` candidate
to `engine.apply_directive(...)` for authoritative evaluation and application.

For small runnable examples, see [examples/basic_usage.py](examples/basic_usage.py)
and [examples/prompt_rendering.py](examples/prompt_rendering.py).

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

from context_compiler_directive_drafter import (
    DirectiveDrafter,
    create_openai_fallback,
)

fallback = create_openai_fallback(
    model="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],
)
drafter = DirectiveDrafter(fallback=fallback, fallback_source="openai")
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

The helper sends the package-owned converter prompt and the original user
input, translating the provider-level `<NO_DIRECTIVE>` abstention sentinel to
the generic fallback callback contract's Python `None` value. Other model text
is returned unchanged. The Drafter remains responsible for parsing, validation,
and result shaping.

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

## Public API

Public interface:

- `DirectiveDrafter()`: Synchronous orchestration over heuristic preprocessing, optional fallback acquisition, fallback output parsing and validation, and final result construction.
- `DraftResult`: Structured non-authoritative result returned by `DirectiveDrafter.draft_directive(...)`.
- `NoDirective` and `UnknownDirective`: Non-canonical drafting result variants with preserved reasons.
- `preprocess_heuristic(message)`: Heuristically draft a candidate directive and, on success, return the `CanonicalDirective` directly.
- `classify_drafter_output(raw_output)`: Classify raw output as directive, no_directive, or unknown.
- `get_converter_prompt()`: Load the shared static converter system prompt.
- `create_openai_fallback(...)`: Create a synchronous OpenAI-compatible fallback callback.
- `create_async_openai_fallback(...)`: Create an asynchronous OpenAI-compatible fallback callback.
- Constants and sentinels exported from the package.

### Output Contract

The intended drafting boundary is:

- input: user text
- output: `DraftResult(source=<final producer>, result=<drafting-layer variant>)`

Every drafting path should end in one of three host-visible result variants:

- `CanonicalDirective`: a proposed canonical directive that is ready for compiler review and independent policy checks
- `NoDirective(reason=...)`: the input is not asking for a directive
- `UnknownDirective(reason=...)`: the input appears directive-related or interpretation failed, but the drafter should not guess

The heuristic uses these outcomes deliberately:

- `NoDirective` means the heuristic has positive evidence that the input is
  confidently non-directive, such as ordinary conversation, a clearly
  non-directive question, or an obvious multi-sentence message reserved for
  host segmentation.
- `UnknownDirective` means the heuristic could not confidently produce one
  candidate and also could not confidently classify the input as non-directive.
  This result is eligible for host fallback interpretation.

Failure to recognize canonical syntax or a bounded rewrite is not, by itself,
evidence for `NoDirective`.

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
Any custom fallback or model-produced candidate output should be classified with
`classify_drafter_output(...)`, then canonical directive text should be
parsed with `context_compiler.grammar.decompose_directive(...)` before it is
shown or used.

For advanced hosts that intentionally compose acquisition themselves, the
recommended boundary is:

```text
preprocess_heuristic(...) [optional]
→ call a provider using get_converter_prompt()
→ classify_drafter_output(raw_output)
→ if classification is directive, parse its canonical text with
  context_compiler.grammar.decompose_directive(...)
→ otherwise abstain, reject, or request clarification
→ send only CanonicalDirective candidates into Core's authoritative workflow
```

`DirectiveDrafter` remains the safer recommended orchestration path because it
owns heuristic/fallback routing and high-level result shaping.

## Current Limits

This package is intentionally conservative. It abstains or returns `unknown`
when input is:

- Ambiguous, mixed-intent, or quoted.
- Embedded in prose, markdown, or code.
- Not safely interpretable as one canonical directive.

Boundary rules:

- Process the full message, not fragments.
- Treat one sentence or one directive request as the acquisition unit. The
  drafter does not perform conversational sentence segmentation.
- Emit at most one canonical directive.
- Abstain when one message contains multiple directive-shaped instructions.
- Do not mine surrounding prose for commands.
- Do not split one message into multiple drafted directives.
- Do not invent new directive semantics.
- Apply only bounded deterministic rewrites that preserve one apparent
  directive operation.
- Defer ambiguous semantic interpretation to the host fallback when available.

Obvious multi-sentence conversational input is outside the acquisition unit.
The heuristic returns `no_directive` for that input rather than sending it to
fallback. The host is responsible for sentence segmentation and may resubmit
the resulting units individually. `unknown` is reserved for an eligible
single acquisition unit that is directive-adjacent but cannot be confidently
reduced to one canonical candidate and may require fallback. Core remains
responsible for canonical directive validity, applicability, authorization,
and execution; it does not own host sentence segmentation.

Questions are directive-adjacent but not explicit directive requests. Forms such
as `allow docker?`, `do not use peanuts?`, and `please use docker?` return an
`unknown` result so a host fallback can interpret them; they never become
heuristic candidates. Clearly non-directive questions such as `can you help
with lunch?` return `no_directive`.

Quoting is intentionally distinct from quoting an operand: a full-message
command such as `"use docker"` is treated as quoted or reported text and is
deferred, while `use "docker"` is a canonical `use` candidate whose operand is
the literal quoted text. The heuristic does not strip operand quotes.

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
