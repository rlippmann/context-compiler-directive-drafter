"""OpenAI-compatible fallback callback factories."""

from collections.abc import Mapping
from importlib import import_module
from typing import Any, cast

from context_compiler_directive_drafter.constants import _PREPROCESSOR_NO_DIRECTIVE_SENTINEL
from context_compiler_directive_drafter.drafter import _AsyncDraftFallback, _DraftFallback


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
) -> dict[str, object]:
    kwargs = dict(request_kwargs or {})
    kwargs["model"] = model
    kwargs["messages"] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_input},
    ]
    return kwargs


def _response_text(response: Any) -> str | None:
    return cast(str | None, response.choices[0].message.content)


def _normalize_response_text(response: Any) -> str | None:
    text = _response_text(response)
    if text is not None and text.strip() == _PREPROCESSOR_NO_DIRECTIVE_SENTINEL:
        return None
    return text


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

    def fallback(user_input: str, prompt: str) -> str | None:
        response = client.chat.completions.create(
            **_request_kwargs(model, user_input, prompt, request_kwargs)
        )
        return _normalize_response_text(response)

    return fallback


def create_async_openai_fallback(
    model: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    request_kwargs: Mapping[str, object] | None = None,
) -> _AsyncDraftFallback:
    """Create an asynchronous OpenAI-compatible Directive Drafter fallback."""
    _, async_openai_client = _load_openai_clients()
    client = async_openai_client(**_client_kwargs(api_key, base_url))

    async def fallback(user_input: str, prompt: str) -> str | None:
        response = await client.chat.completions.create(
            **_request_kwargs(model, user_input, prompt, request_kwargs)
        )
        return _normalize_response_text(response)

    return fallback
