# Context Compiler Directive Drafter

Draft candidate Context Compiler directives from natural-language input.

For example, the drafter can turn:

> Please use Docker for container examples.

into the candidate directive:

> use docker

Drafts are non-authoritative. `context-compiler` remains responsible for
grammar validity, policy decisions, application, and authoritative state.

## Installation

```bash
pip install "context-compiler-directive-drafter"
```

For local development:

```bash
uv sync --group dev
```

## Basic usage

```python
from context_compiler_directive_drafter import (
    DirectiveDrafter,
    RejectedDirective,
    UnknownDirective,
)

result = DirectiveDrafter().draft_directive(
    "Please use Docker for container examples."
)

if hasattr(result.result, "text"):
    print("Candidate directive:", result.result.text)
elif isinstance(result.result, RejectedDirective):
    print("Directive acquisition rejected:", result.result.reason)
elif isinstance(result.result, UnknownDirective):
    print("Need clarification:", result.result.reason)
```

`DraftResult.result` is one of three high-level outcomes:

- `CanonicalDirective`: a proposed directive for host review;
- `RejectedDirective`: terminal acquisition rejection that is not sent to fallback;
- `UnknownDirective`: semantic uncertainty eligible for optional fallback acquisition.

The `source` field identifies the final producer, such as `heuristic` or a
configured fallback source. It does not represent compiler approval or applied
state. For a runnable example, see [examples/basic_usage.py](examples/basic_usage.py).

## Fallback integrations

The drafter always tries heuristic drafting first. Configure a fallback when
the host wants provider-backed interpretation of `UnknownDirective` results.
Fallback callbacks receive the original input and return candidate directive
text or `None`.

### OpenAI-compatible providers

```bash
pip install "context-compiler-directive-drafter[openai]"
```

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

Use `create_async_openai_fallback(...)` with
`DirectiveDrafter(async_fallback=...)` and `async_draft_directive(...)` for an
asynchronous host path. OpenAI-compatible endpoints can provide a custom
`base_url`.

### LiteLLM

```bash
pip install "context-compiler-directive-drafter[litellm]"
```

```python
from context_compiler_directive_drafter.fallbacks.litellm import create_litellm_fallback

fallback = create_litellm_fallback(model="anthropic/claude-sonnet-4-5")
```

Pass LiteLLM's provider/model identifier unchanged. For native integrations,
the [`fallbacks` namespace](src/context_compiler_directive_drafter/fallbacks/__init__.py)
provides provider-neutral callback types, fallback profiles, structured-response
parsing, and invalid-response errors.

Provider adapters handle provider response formats. The Drafter uses Core
grammar parsing and validation for returned candidate text and constructs the
non-authoritative result.

## Authority boundary

The Drafter proposes; the Context Compiler decides and applies. Hosts should
review or confirm a `CanonicalDirective` before handing it to Core. Never pass
raw provider output directly to the compiler, and do not use the Drafter to
read or mutate authoritative compiler state.

The drafter's acquisition rules, including rejection, uncertainty, bounded
rewrites, and other input-boundary behavior, are specified in
[DrafterAcquisitionSpec.md](docs/DrafterAcquisitionSpec.md).

## Further documentation

- [Acquisition specification](docs/DrafterAcquisitionSpec.md)
- [Contributor guidance](CONTRIBUTING.md)
- [English evaluation data and review workflow](docs/EnglishEvaluationCorpus.md)

## Development

```bash
uv run pre-commit run --all-files
uv run pytest
```

The shared compatibility fixtures under `tests/fixtures/` are the executable
authority for portable behavior; detailed fixture and evaluation material is
kept out of this entry-point document.

## License

Apache-2.0
