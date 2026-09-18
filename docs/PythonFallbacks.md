# Python fallback integrations

Directive Drafter fallbacks are Python callbacks that receive the original user
input and return candidate directive text or `None`. The Drafter uses them only
for results that are eligible for fallback acquisition, such as
`UnknownDirective`.

Provider adapters handle provider response formats. The Drafter passes returned
candidate text through Context Compiler grammar parsing and validation before
constructing its non-authoritative result. Do not pass raw provider output
directly to Context Compiler.

## OpenAI-compatible providers

Install the optional integration:

```bash
pip install "context-compiler-directive-drafter[openai]"
```

Create a fallback callback and configure it on the Drafter:

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
`DirectiveDrafter(async_fallback=...)` and
`async_draft_directive(...)` for an asynchronous host path. OpenAI-compatible
endpoints can provide a custom `base_url`.

## LiteLLM

Install the optional integration:

```bash
pip install "context-compiler-directive-drafter[litellm]"
```

```python
from context_compiler_directive_drafter.fallbacks.litellm import create_litellm_fallback

fallback = create_litellm_fallback(model="anthropic/claude-sonnet-4-5")
```

Pass LiteLLM's provider/model identifier unchanged. Native integrations can
reuse the provider-neutral API in the
[`fallbacks` namespace](../src/context_compiler_directive_drafter/fallbacks/__init__.py),
including callback types, fallback profiles, structured-response parsing, and
invalid-response errors.
