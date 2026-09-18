# Context Compiler Directive Drafter

Directive Drafter turns user input into non-authoritative candidate directives
for host review. It combines deterministic heuristic drafting with an optional
fallback acquisition step for input the heuristic path cannot interpret
confidently.

The Drafter proposes. Context Compiler remains authoritative for grammar,
policy decisions, application, and state.

## Installation

```bash
pip install "context-compiler-directive-drafter"
```

For local development:

```bash
uv sync --group dev
```

## Basic usage

This Python example uses the deterministic heuristic path:

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
result = drafter.draft_directive("I prefer concise replies")

if isinstance(result.result, CanonicalDirective):
    print("Candidate directive:", result.result.text)  # use concise replies
    if input("Confirm and apply this directive? [y/N] ").lower() == "y":
        decision = engine.apply_directive(result.result)
        print("Compiler decision:", decision)
elif isinstance(result.result, RejectedDirective):
    print("Directive acquisition rejected:", result.result.reason)
elif isinstance(result.result, UnknownDirective):
    print("Need clarification or optional fallback:", result.result.reason)
```

`DraftResult.result` has one of three high-level forms:

- `CanonicalDirective`: a candidate directive for host review;
- `RejectedDirective`: a terminal acquisition rejection;
- `UnknownDirective`: semantic uncertainty that may be sent to an optional
  fallback.

The `source` field identifies the producer of the final drafting result. It does
not represent compiler approval, applied state, or authoritative state.

## Optional fallbacks

Fallbacks are optional acquisition integrations for `UnknownDirective` results.
They receive the original input and may propose candidate directive text for
the host to review. For example, a fallback may interpret:

> The intended audience is senior management

as:

> `set premise intended audience is senior management`

The premise interpretation depends on optional fallback acquisition; it is not
claimed as deterministic heuristic behavior. Available fallback integrations
depend on the implementation. See the [Python fallback integrations](docs/PythonFallbacks.md)
document for provider-specific setup.

## Authority boundary

Hosts decide whether to confirm a proposed `CanonicalDirective`. Only after
confirmation should a host hand it to Context Compiler through
`engine.apply_directive(...)`. Do not pass raw fallback output directly to the
compiler, and do not use the Drafter to read or mutate authoritative compiler
state.

## Further documentation

- [Acquisition specification](docs/DrafterAcquisitionSpec.md)
- [Python fallback integrations](docs/PythonFallbacks.md)
- [Contributor guidance](CONTRIBUTING.md)

## Development

```bash
uv run pre-commit run --all-files
uv run pytest
```

## License

Apache-2.0
