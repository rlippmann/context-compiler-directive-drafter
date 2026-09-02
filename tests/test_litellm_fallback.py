import asyncio
import subprocess
import sys
from types import SimpleNamespace

import pytest
from context_compiler.grammar import DirectiveKind

from context_compiler_directive_drafter.fallbacks import (
    InvalidFallbackResponseError,
    get_fallback_profile,
)
from context_compiler_directive_drafter.fallbacks import litellm as adapter


class _FakeResponse:
    def __init__(self, content: str | None) -> None:
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]


class _FakeLiteLLM:
    supports_schema = False
    response = _FakeResponse("use docker")
    error: Exception | None = None
    completion_calls: list[dict[str, object]] = []
    async_completion_calls: list[dict[str, object]] = []
    support_checks: list[str] = []

    @classmethod
    def reset(cls) -> None:
        cls.supports_schema = False
        cls.response = _FakeResponse("use docker")
        cls.error = None
        cls.completion_calls = []
        cls.async_completion_calls = []
        cls.support_checks = []

    @classmethod
    def supports_response_schema(cls, *, model: str) -> bool:
        cls.support_checks.append(model)
        return cls.supports_schema

    @classmethod
    def completion(cls, **kwargs: object) -> _FakeResponse:
        cls.completion_calls.append(kwargs)
        if cls.error is not None:
            raise cls.error
        return cls.response

    @classmethod
    async def acompletion(cls, **kwargs: object) -> _FakeResponse:
        cls.async_completion_calls.append(kwargs)
        if cls.error is not None:
            raise cls.error
        return cls.response


@pytest.fixture(autouse=True)
def _reset_fake_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeLiteLLM.reset()
    monkeypatch.setattr(adapter, "import_module", lambda name: _FakeLiteLLM)


def test_sync_free_text_uses_profile_prompt_sentinel_and_model_identifier() -> None:
    _FakeLiteLLM.response = _FakeResponse("  <NO_DIRECTIVE> \n")

    fallback = adapter.create_litellm_fallback(
        "anthropic/claude-sonnet",
        api_key="key",
        api_base="https://proxy.example",
        request_kwargs={"temperature": 0, "response_format": {"type": "json_object"}},
    )

    assert fallback("original input") is None
    assert _FakeLiteLLM.support_checks == ["anthropic/claude-sonnet"]
    assert _FakeLiteLLM.completion_calls == [
        {
            "temperature": 0,
            "api_key": "key",
            "api_base": "https://proxy.example",
            "model": "anthropic/claude-sonnet",
            "messages": [
                {"role": "system", "content": get_fallback_profile().system_prompt},
                {"role": "user", "content": "original input"},
            ],
        }
    ]


def test_sync_structured_path_passes_profile_schema_and_parses_rejection() -> None:
    _FakeLiteLLM.supports_schema = True
    _FakeLiteLLM.response = _FakeResponse('{"classification":"rejected","output":null}')

    fallback = adapter.create_litellm_fallback("openai/gpt-4o-mini")

    assert fallback("input") is None
    call = _FakeLiteLLM.completion_calls[0]
    assert call["messages"] == [
        {"role": "system", "content": get_fallback_profile(structured_output=True).system_prompt},
        {"role": "user", "content": "input"},
    ]
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "directive_drafter_result",
            "strict": True,
            "schema": get_fallback_profile(structured_output=True).response_schema,
        },
    }


def test_allowed_directive_kinds_are_rendered_in_litellm_profile() -> None:
    allowed = {DirectiveKind.USE_ITEM}
    fallback = adapter.create_litellm_fallback(
        "openai/gpt-4o-mini", allowed_directive_kinds=allowed
    )

    assert fallback("input") == "use docker"
    assert (
        _FakeLiteLLM.completion_calls[0]["messages"][0]["content"]
        == get_fallback_profile(allowed_directive_kinds=allowed).system_prompt
    )


def test_async_free_text_path_uses_profile_sentinel() -> None:
    _FakeLiteLLM.response = _FakeResponse("<NO_DIRECTIVE>")

    fallback = asyncio.run(adapter.create_async_litellm_fallback("gemini/gemini-2.0-flash"))

    assert asyncio.run(fallback("input")) is None
    assert _FakeLiteLLM.async_completion_calls[0]["model"] == "gemini/gemini-2.0-flash"


def test_async_structured_path_parses_directive() -> None:
    _FakeLiteLLM.supports_schema = True
    _FakeLiteLLM.response = _FakeResponse('{"classification":"directive","output":"use docker"}')

    fallback = asyncio.run(adapter.create_async_litellm_fallback("openai/gpt-4o-mini"))

    assert asyncio.run(fallback("input")) == "use docker"


def test_structured_malformed_response_uses_existing_error() -> None:
    _FakeLiteLLM.supports_schema = True
    _FakeLiteLLM.response = _FakeResponse("not json")
    fallback = adapter.create_litellm_fallback("openai/gpt-4o-mini")

    with pytest.raises(InvalidFallbackResponseError):
        fallback("input")


def test_provider_errors_remain_errors() -> None:
    _FakeLiteLLM.error = RuntimeError("provider unavailable")
    fallback = adapter.create_litellm_fallback("openai/gpt-4o-mini")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        fallback("input")


def test_missing_optional_dependency_has_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def import_without_litellm(name: str) -> object:
        if name == "litellm":
            raise ImportError("litellm is unavailable")
        raise AssertionError(f"unexpected optional import: {name}")

    monkeypatch.setattr(adapter, "import_module", import_without_litellm)

    with pytest.raises(RuntimeError, match=r"pip install .*\[litellm\]"):
        adapter.create_litellm_fallback("openai/gpt-4o-mini")


def test_base_package_import_does_not_require_litellm() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import context_compiler_directive_drafter"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
