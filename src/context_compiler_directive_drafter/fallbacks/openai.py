"""OpenAI-compatible fallback callback factories.

This adapter owns OpenAI request and capability handling; acquisition
instructions and response semantics come from the public ``fallbacks`` facade.
"""

import json
from collections.abc import Callable, Collection, Mapping
from importlib import import_module
from typing import Any, cast

from context_compiler.grammar import DirectiveKind

from context_compiler_directive_drafter.fallbacks import (
    AsyncDraftFallback,
    DraftFallback,
    InvalidFallbackResponseError,
    get_fallback_profile,
    parse_structured_response,
)

_STRUCTURED_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "directive_drafter_result",
        "strict": True,
        "schema": get_fallback_profile(structured_output=True).response_schema,
    },
}
_PROBE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "structured_output_probe",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
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


def _select_transport(
    structured_output: bool,
    allowed_directive_kinds: Collection[DirectiveKind] | None = None,
) -> tuple[str, object | None, Callable[[Any], str | None]]:
    profile = get_fallback_profile(
        structured_output=structured_output,
        allowed_directive_kinds=allowed_directive_kinds,
    )
    if profile.mode == "structured":
        return (
            profile.system_prompt,
            _STRUCTURED_RESPONSE_FORMAT,
            _structured_response_text,
        )

    def parse_response(response: Any) -> str | None:
        return _normalize_response_text(response, profile.abstention_sentinel)

    return (
        profile.system_prompt,
        None,
        parse_response,
    )


def _probe_request_kwargs(model: str) -> dict[str, object]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": 'Return exactly {"ok":true}.'},
            {"role": "user", "content": "Probe structured-output support."},
        ],
        "response_format": _PROBE_RESPONSE_FORMAT,
    }


def _is_unsupported_structured_output_error(error: Exception) -> bool:
    message = str(error).lower()
    mentions_format = any(
        term in message for term in ("response_format", "json schema", "structured output")
    )
    indicates_unsupported = any(
        term in message
        for term in (
            "not supported",
            "unsupported",
            "does not support",
            "unrecognized",
            "unknown parameter",
            "invalid parameter",
        )
    )
    return mentions_format and indicates_unsupported


def _probe_structured_output(client: Any, model: str) -> bool:
    try:
        response = client.chat.completions.create(**_probe_request_kwargs(model))
    except Exception as error:
        if _is_unsupported_structured_output_error(error):
            return False
        raise
    return _probe_response_conforms(response)


async def _probe_structured_output_async(client: Any, model: str) -> bool:
    try:
        response = await client.chat.completions.create(**_probe_request_kwargs(model))
    except Exception as error:
        if _is_unsupported_structured_output_error(error):
            return False
        raise
    return _probe_response_conforms(response)


def _probe_response_conforms(response: Any) -> bool:
    content = _response_text(response)
    if not isinstance(content, str):
        return False
    try:
        envelope = json.loads(content)
    except json.JSONDecodeError:
        return False
    return isinstance(envelope, dict) and envelope == {"ok": True}


def _response_text(response: Any) -> str | None:
    return cast(str | None, response.choices[0].message.content)


def _normalize_response_text(response: Any, abstention_sentinel: str | None) -> str | None:
    text = _response_text(response)
    if text is not None and abstention_sentinel is not None and text.strip() == abstention_sentinel:
        return None
    return text


def _structured_response_text(response: Any) -> str | None:
    content = _response_text(response)
    if not isinstance(content, str):
        raise InvalidFallbackResponseError("structured fallback response content is not text")
    return parse_structured_response(content)


def create_openai_fallback(
    model: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    request_kwargs: Mapping[str, object] | None = None,
    allowed_directive_kinds: Collection[DirectiveKind] | None = None,
) -> DraftFallback:
    """Create a synchronous OpenAI-compatible Directive Drafter fallback.

    ``allowed_directive_kinds`` is forwarded to the provider-neutral fallback
    profile and limits the kinds the provider is instructed to propose.
    """
    openai_client, _ = _load_openai_clients()
    client = openai_client(**_client_kwargs(api_key, base_url))
    structured_output = _probe_structured_output(client, model)
    prompt, response_format, parse_response = _select_transport(
        structured_output, allowed_directive_kinds
    )

    def fallback(user_input: str) -> str | None:
        response = client.chat.completions.create(
            **_request_kwargs(model, user_input, prompt, request_kwargs, response_format)
        )
        return parse_response(response)

    return fallback


async def create_async_openai_fallback(
    model: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    request_kwargs: Mapping[str, object] | None = None,
    allowed_directive_kinds: Collection[DirectiveKind] | None = None,
) -> AsyncDraftFallback:
    """Create an asynchronous OpenAI-compatible Directive Drafter fallback.

    ``allowed_directive_kinds`` is forwarded to the provider-neutral fallback
    profile and limits the kinds the provider is instructed to propose.
    """
    _, async_openai_client = _load_openai_clients()
    client = async_openai_client(**_client_kwargs(api_key, base_url))
    structured_output = await _probe_structured_output_async(client, model)
    prompt, response_format, parse_response = _select_transport(
        structured_output, allowed_directive_kinds
    )

    async def fallback(user_input: str) -> str | None:
        response = await client.chat.completions.create(
            **_request_kwargs(model, user_input, prompt, request_kwargs, response_format)
        )
        return parse_response(response)

    return fallback
