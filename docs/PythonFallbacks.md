# Python fallback integrations

Directive Drafter fallbacks are Python callbacks that receive the original user
input and return candidate directive text or `None`. The Drafter uses them only
for `UnknownDirective` results, which are the only results eligible for fallback
acquisition.

Provider adapters handle provider response formats. The Drafter passes returned
candidate text through Context Compiler grammar parsing and validation before
constructing its non-authoritative result.

## OpenAI-compatible providers

Install the optional integration:

```bash
pip install "context-compiler-directive-drafter[openai]"
```

Create a fallback callback and configure it on the Drafter:

```python
import os

from context_compiler_directive_drafter import DirectiveDrafter
from context_compiler_directive_drafter.fallbacks.openai import (
    create_async_openai_fallback,
    create_openai_fallback,
)

fallback = create_openai_fallback(
    model="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],
)
drafter = DirectiveDrafter(fallback=fallback, fallback_source="openai")
```

Await `create_async_openai_fallback(...)` to obtain the callback, then configure
it with `async_fallback_source="openai"`:

```python
async_fallback = await create_async_openai_fallback(model="gpt-4o-mini")
drafter = DirectiveDrafter(
    async_fallback=async_fallback,
    async_fallback_source="openai",
)
```

Use `async_draft_directive(...)` for the asynchronous host path. Set the source
explicitly because the async source is configured separately. OpenAI-compatible
endpoints can provide a custom `base_url`.

## LiteLLM

Install the optional integration:

```bash
pip install "context-compiler-directive-drafter[litellm]"
```

```python
from context_compiler_directive_drafter import DirectiveDrafter
from context_compiler_directive_drafter.fallbacks.litellm import create_litellm_fallback

fallback = create_litellm_fallback(model="anthropic/claude-sonnet-4-5")
drafter = DirectiveDrafter(fallback=fallback, fallback_source="litellm")
```

Pass LiteLLM's provider/model identifier unchanged. Native integrations can
reuse the provider-neutral API in the
[`fallbacks` namespace](../src/context_compiler_directive_drafter/fallbacks/__init__.py),
including callback types, fallback profiles, structured-response parsing, and
invalid-response errors.
