# Context Compiler Directive Drafter

Directive Drafter helps turn a user's words into a possible Context Compiler
directive. It starts with predictable rules. You can add an optional fallback
for requests those rules cannot understand with confidence.

The Drafter only makes suggestions. Context Compiler makes the final decision
and is the only component that applies a directive or changes saved state.

## Installation

```bash
pip install "context-compiler-directive-drafter"
```

For development:

```bash
uv sync --group dev
```

## Basic usage

This example uses the built-in rules. It turns `I prefer concise replies` into
`use concise replies`:

```python
from context_compiler import Engine
from context_compiler.grammar import CanonicalDirective

from context_compiler_directive_drafter import (
    DirectiveDrafter,
    RejectedDirective,
    UnknownDirective,
)

drafter = DirectiveDrafter()
engine = Engine()
draft_result = drafter.draft_directive("I prefer concise replies")

if isinstance(draft_result.result, CanonicalDirective):
    print("Candidate directive:", draft_result.result.text)  # use concise replies
    if input("Confirm and apply this directive? [y/N] ").lower() == "y":
        decision = engine.apply_directive(draft_result.result)
        print("Compiler decision:", decision)
elif isinstance(draft_result.result, RejectedDirective):
    print("Directive acquisition rejected:", draft_result.result.reason)
elif isinstance(draft_result.result, UnknownDirective):
    print("Need clarification or optional fallback:", draft_result.result.reason)
```

`DraftResult.result` can be one of three things:

- `CanonicalDirective`: a possible directive for the host to review;
- `RejectedDirective`: drafting ended with a terminal rejection and no candidate directive;
- `UnknownDirective`: the input is unclear and may be sent to an optional
  fallback.

The `source` field says where the result came from. It does not mean that the
compiler approved the result or applied it.

## Optional fallbacks

Directive Drafter has two acquisition paths. The built-in heuristic path uses
deterministic, bounded recognition and rewrite rules. An optional semantic
fallback handles eligible inputs that the heuristic path leaves unresolved. A
semantic fallback may use a model or another implementation, and is not needed
for basic Directive Drafter use.

Fallbacks are optional helpers for `UnknownDirective` results. They receive the
original input and may suggest directive text for the host to review. For
example, a fallback may interpret:

> The intended audience is senior management

as:

> `set premise intended audience is senior management`

The premise example needs a fallback; the built-in rules do not interpret it on
their own. Available fallback integrations depend on the implementation. See
the [Python fallback integrations](docs/PythonFallbacks.md) document for
provider-specific setup.

## Authority boundary

The host decides whether to accept a proposed `CanonicalDirective`. After the
user confirms it, the host can pass it to Context Compiler with
`engine.apply_directive(...)`. Drafter-produced `CanonicalDirective` candidates
are the reviewed handoff for this workflow. The Drafter must not read or change
compiler state.

## Further documentation

- [Acquisition specification](docs/DrafterAcquisitionSpec.md)
- [English evaluation data](docs/EnglishEvaluationCorpus.md)
- [Python fallback integrations](docs/PythonFallbacks.md)
- [Contributor guidance](CONTRIBUTING.md)

## Development

```bash
uv run pre-commit run --all-files
uv run pytest
```

## License

Apache-2.0
