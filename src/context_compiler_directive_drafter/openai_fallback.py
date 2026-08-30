"""OpenAI-compatible fallback callback factories."""

import json
from collections.abc import Mapping
from importlib import import_module
from typing import Any, cast

from context_compiler_directive_drafter._prompts import (
    _get_converter_prompt,
    _get_structured_converter_prompt,
)
from context_compiler_directive_drafter.constants import _PREPROCESSOR_NO_DIRECTIVE_SENTINEL
from context_compiler_directive_drafter.drafter import (
    InvalidFallbackResponseError,
    _AsyncDraftFallback,
    _DraftFallback,
)

_STRUCTURED_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "directive_drafter_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "classification": {"type": "string", "enum": ["directive", "rejected"]},
                "output": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            },
            "required": ["classification", "output"],
            "additionalProperties": False,
        },
    },
}


def _load_openai_clients() -> tuple[type[Any], type[Any]]:
    try:
        openai = import_module("openai")
    except ImportError as exc:
        raise RuntimeError(
            "The OpenAI-compatible fallback requires the optional dependency; "
            "install it with `pip install context-compiler-directive-drafter[openai]`."
        ) from exc
    return cast(type[Any], openai.OpenAI), cast(type[Any], openai.AsyncOpenAI)


def _client_kwargs(api_key: str | None, base_url: str | None) -> dict[str, str]:
    kwargs: dict[str, str] = {}
    if api_key is not None:
        kwargs["api_key"] = api_key
    if base_url is not None:
        kwargs["base_url"] = base_url
    return kwargs


def _request_kwargs(
    model: str,
    user_input: str,
    prompt: str,
    request_kwargs: Mapping[str, object] | None,
    response_format: object | None = None,
) -> dict[str, object]:
    kwargs = dict(request_kwargs or {})
    kwargs.pop("response_format", None)
    kwargs["model"] = model
    kwargs["messages"] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_input},
    ]
    if response_format is not None:
        kwargs["response_format"] = response_format
    return kwargs


def _resolve_structured_output_capability(client: Any, model: str) -> bool:
    """Resolve structured-output support once from provider model metadata."""

    models = getattr(client, "models", None)
    retrieve = getattr(models, "retrieve", None)
    if retrieve is None:
        return False
    metadata = retrieve(model)
    capabilities = getattr(metadata, "capabilities", None)
    if not isinstance(capabilities, Mapping):
        return False
    return any(
        capabilities.get(name) is True
        for name in ("structured_outputs", "structured_output", "json_schema")
    )


def _response_text(response: Any) -> str | None:
    return cast(str | None, response.choices[0].message.content)


def _normalize_response_text(response: Any) -> str | None:
    text = _response_text(response)
    if text is not None and text.strip() == _PREPROCESSOR_NO_DIRECTIVE_SENTINEL:
        return None
    return text


def _structured_response_text(response: Any) -> str | None:
    content = _response_text(response)
    if not isinstance(content, str):
        raise InvalidFallbackResponseError("structured fallback response content is not text")
    try:
        envelope = json.loads(content)
    except json.JSONDecodeError as exc:
        raise InvalidFallbackResponseError("structured fallback response is not JSON") from exc
    if not isinstance(envelope, dict) or set(envelope) != {"classification", "output"}:
        raise InvalidFallbackResponseError("structured fallback response has an invalid envelope")
    classification = envelope["classification"]
    output = envelope["output"]
    if classification == "directive" and isinstance(output, str):
        return output
    if classification == "rejected" and output is None:
        return None
    raise InvalidFallbackResponseError("structured fallback response is inconsistent")


def create_openai_fallback(
    model: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    request_kwargs: Mapping[str, object] | None = None,
) -> _DraftFallback:
    """Create a synchronous OpenAI-compatible Directive Drafter fallback."""
    openai_client, _ = _load_openai_clients()
    client = openai_client(**_client_kwargs(api_key, base_url))
    structured_output = _resolve_structured_output_capability(client, model)
    if structured_output:
        prompt = _get_structured_converter_prompt()
        response_format = _STRUCTURED_RESPONSE_FORMAT
        parse_response = _structured_response_text
    else:
        prompt = _get_converter_prompt()
        response_format = None
        parse_response = _normalize_response_text

    def fallback(user_input: str) -> str | None:
        response = client.chat.completions.create(
            **_request_kwargs(model, user_input, prompt, request_kwargs, response_format)
        )
        return parse_response(response)

    return fallback


def create_async_openai_fallback(
    model: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    request_kwargs: Mapping[str, object] | None = None,
) -> _AsyncDraftFallback:
    """Create an asynchronous OpenAI-compatible Directive Drafter fallback."""
    openai_client, async_openai_client = _load_openai_clients()
    capability_client = openai_client(**_client_kwargs(api_key, base_url))
    client = async_openai_client(**_client_kwargs(api_key, base_url))
    structured_output = _resolve_structured_output_capability(capability_client, model)
    if structured_output:
        prompt = _get_structured_converter_prompt()
        response_format = _STRUCTURED_RESPONSE_FORMAT
        parse_response = _structured_response_text
    else:
        prompt = _get_converter_prompt()
        response_format = None
        parse_response = _normalize_response_text

    async def fallback(user_input: str) -> str | None:
        response = await client.chat.completions.create(
            **_request_kwargs(model, user_input, prompt, request_kwargs, response_format)
        )
        return parse_response(response)

    return fallback
