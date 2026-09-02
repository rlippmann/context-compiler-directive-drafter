"""LiteLLM fallback callback factories.

This adapter owns LiteLLM request and capability handling; acquisition
instructions and response semantics come from the public ``fallbacks`` facade.
"""

from collections.abc import Callable, Collection, Mapping
from importlib import import_module
from types import ModuleType
from typing import Any, cast

from context_compiler.grammar import DirectiveKind

from context_compiler_directive_drafter.fallbacks import (
    AsyncDraftFallback,
    DraftFallback,
    FallbackProfile,
    InvalidFallbackResponseError,
    get_fallback_profile,
    parse_structured_response,
)

_STRUCTURED_PROBE_INPUT = "Probe structured-output support."


def _load_litellm() -> ModuleType:
    try:
        return import_module("litellm")
    except ImportError as exc:
        raise RuntimeError(
            "The LiteLLM fallback requires the optional dependency; install it with "
            "`pip install context-compiler-directive-drafter[litellm]`."
        ) from exc


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


def _structured_response_format(profile: FallbackProfile) -> dict[str, object]:
    schema = profile.response_schema
    if schema is None:
        raise RuntimeError("structured LiteLLM fallback profile has no response schema")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "directive_drafter_result",
            "strict": True,
            "schema": schema,
        },
    }


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


def _probe_request_kwargs(
    model: str,
    profile: FallbackProfile,
    request_kwargs: Mapping[str, object],
) -> dict[str, object]:
    response_format = _structured_response_format(profile)
    return _request_kwargs(
        model,
        _STRUCTURED_PROBE_INPUT,
        profile.system_prompt,
        request_kwargs,
        response_format,
    )


def _probe_structured_output(
    litellm: ModuleType,
    model: str,
    request_kwargs: Mapping[str, object],
    allowed_directive_kinds: Collection[DirectiveKind] | None,
) -> bool:
    profile = get_fallback_profile(
        structured_output=True,
        allowed_directive_kinds=allowed_directive_kinds,
    )
    try:
        litellm.completion(**_probe_request_kwargs(model, profile, request_kwargs))
    except Exception as error:
        if _is_unsupported_structured_output_error(error):
            return False
        raise
    return True


async def _probe_structured_output_async(
    litellm: ModuleType,
    model: str,
    request_kwargs: Mapping[str, object],
    allowed_directive_kinds: Collection[DirectiveKind] | None,
) -> bool:
    profile = get_fallback_profile(
        structured_output=True,
        allowed_directive_kinds=allowed_directive_kinds,
    )
    try:
        await litellm.acompletion(**_probe_request_kwargs(model, profile, request_kwargs))
    except Exception as error:
        if _is_unsupported_structured_output_error(error):
            return False
        raise
    return True


def _select_transport(
    model: str,
    allowed_directive_kinds: Collection[DirectiveKind] | None,
    structured_output: bool,
) -> tuple[FallbackProfile, object | None, Callable[[Any], str | None]]:
    profile = get_fallback_profile(
        structured_output=structured_output,
        allowed_directive_kinds=allowed_directive_kinds,
    )
    if profile.mode == "structured":
        return profile, _structured_response_format(profile), _structured_response_text

    def parse_response(response: Any) -> str | None:
        return _normalize_response_text(response, profile.abstention_sentinel)

    return profile, None, parse_response


def create_litellm_fallback(
    model: str,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    request_kwargs: Mapping[str, object] | None = None,
    allowed_directive_kinds: Collection[DirectiveKind] | None = None,
) -> DraftFallback:
    """Create a synchronous LiteLLM Directive Drafter fallback.

    ``model`` is passed unchanged to LiteLLM, including any provider prefix.
    ``allowed_directive_kinds`` is forwarded to the provider-neutral fallback
    profile and limits the kinds the provider is instructed to propose.
    """
    litellm = _load_litellm()
    call_kwargs = dict(request_kwargs or {})
    if api_key is not None:
        call_kwargs["api_key"] = api_key
    if api_base is not None:
        call_kwargs["api_base"] = api_base
    structured_output = bool(litellm.supports_response_schema(model=model))
    if not structured_output:
        structured_output = _probe_structured_output(
            litellm, model, call_kwargs, allowed_directive_kinds
        )
    profile, response_format, parse_response = _select_transport(
        model, allowed_directive_kinds, structured_output
    )

    def fallback(user_input: str) -> str | None:
        response = litellm.completion(
            **_request_kwargs(
                model, user_input, profile.system_prompt, call_kwargs, response_format
            )
        )
        return parse_response(response)

    return fallback


async def create_async_litellm_fallback(
    model: str,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    request_kwargs: Mapping[str, object] | None = None,
    allowed_directive_kinds: Collection[DirectiveKind] | None = None,
) -> AsyncDraftFallback:
    """Create an asynchronous LiteLLM Directive Drafter fallback.

    ``model`` is passed unchanged to LiteLLM, including any provider prefix.
    ``allowed_directive_kinds`` is forwarded to the provider-neutral fallback
    profile and limits the kinds the provider is instructed to propose.
    """
    litellm = _load_litellm()
    call_kwargs = dict(request_kwargs or {})
    if api_key is not None:
        call_kwargs["api_key"] = api_key
    if api_base is not None:
        call_kwargs["api_base"] = api_base
    structured_output = bool(litellm.supports_response_schema(model=model))
    if not structured_output:
        structured_output = await _probe_structured_output_async(
            litellm, model, call_kwargs, allowed_directive_kinds
        )
    profile, response_format, parse_response = _select_transport(
        model, allowed_directive_kinds, structured_output
    )

    async def fallback(user_input: str) -> str | None:
        response = await litellm.acompletion(
            **_request_kwargs(
                model, user_input, profile.system_prompt, call_kwargs, response_format
            )
        )
        return parse_response(response)

    return fallback
