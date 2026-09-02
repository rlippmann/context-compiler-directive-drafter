import asyncio
import subprocess
import sys
from types import SimpleNamespace

import pytest
from context_compiler.grammar import DirectiveKind

from context_compiler_directive_drafter.fallbacks import (
    FallbackProfile,
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
    probe_error: Exception | None = RuntimeError("response_format is not supported")
    completion_calls: list[dict[str, object]] = []
    async_completion_calls: list[dict[str, object]] = []
    probe_calls: list[dict[str, object]] = []
    async_probe_calls: list[dict[str, object]] = []
    support_checks: list[str] = []

    @classmethod
    def reset(cls) -> None:
        cls.supports_schema = False
        cls.response = _FakeResponse("use docker")
        cls.error = None
        cls.probe_error = RuntimeError("response_format is not supported")
        cls.completion_calls = []
        cls.async_completion_calls = []
        cls.probe_calls = []
        cls.async_probe_calls = []
        cls.support_checks = []

    @classmethod
    def supports_response_schema(cls, *, model: str) -> bool:
        cls.support_checks.append(model)
        return cls.supports_schema

    @classmethod
    def completion(cls, **kwargs: object) -> _FakeResponse:
        messages = kwargs["messages"]
        is_probe = messages[1]["content"] == adapter._STRUCTURED_PROBE_INPUT
        (cls.probe_calls if is_probe else cls.completion_calls).append(kwargs)
        if is_probe and cls.probe_error is not None:
            error = cls.probe_error
            cls.probe_error = None
            raise error
        if cls.error is not None:
            raise cls.error
        return cls.response

    @classmethod
    async def acompletion(cls, **kwargs: object) -> _FakeResponse:
        messages = kwargs["messages"]
        is_probe = messages[1]["content"] == adapter._STRUCTURED_PROBE_INPUT
        (cls.async_probe_calls if is_probe else cls.async_completion_calls).append(kwargs)
        if is_probe and cls.probe_error is not None:
            error = cls.probe_error
            cls.probe_error = None
            raise error
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


def test_successful_structured_probe_selects_structured_path() -> None:
    _FakeLiteLLM.probe_error = None
    _FakeLiteLLM.response = _FakeResponse('{"classification":"directive","output":"use docker"}')

    fallback = adapter.create_litellm_fallback("ollama/qwen2.5:14b-instruct")

    assert fallback("input") == "use docker"
    assert "response_format" in _FakeLiteLLM.probe_calls[0]
    assert "response_format" in _FakeLiteLLM.completion_calls[0]


def test_sync_structured_request_downgrades_only_when_unsupported() -> None:
    _FakeLiteLLM.response = _FakeResponse("use docker")

    fallback = adapter.create_litellm_fallback("ollama/qwen2.5:14b-instruct")

    assert fallback("input") == "use docker"
    assert "response_format" in _FakeLiteLLM.probe_calls[0]
    assert "response_format" not in _FakeLiteLLM.completion_calls[0]
    assert (
        _FakeLiteLLM.completion_calls[0]["messages"][0]["content"]
        == get_fallback_profile().system_prompt
    )


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

    fallback = asyncio.run(
        adapter.create_async_litellm_fallback(
            "gemini/gemini-2.0-flash",
            api_key="key",
            api_base="https://proxy.example",
        )
    )

    assert asyncio.run(fallback("input")) is None
    call = _FakeLiteLLM.async_completion_calls[0]
    assert call["model"] == "gemini/gemini-2.0-flash"
    assert call["api_key"] == "key"
    assert call["api_base"] == "https://proxy.example"


def test_async_structured_path_parses_directive() -> None:
    _FakeLiteLLM.supports_schema = True
    _FakeLiteLLM.response = _FakeResponse('{"classification":"directive","output":"use docker"}')

    fallback = asyncio.run(adapter.create_async_litellm_fallback("openai/gpt-4o-mini"))

    assert asyncio.run(fallback("input")) == "use docker"


def test_async_successful_structured_probe_selects_structured_path() -> None:
    _FakeLiteLLM.probe_error = None
    _FakeLiteLLM.response = _FakeResponse('{"classification":"directive","output":"use docker"}')

    fallback = asyncio.run(adapter.create_async_litellm_fallback("ollama/qwen2.5:14b-instruct"))

    assert asyncio.run(fallback("input")) == "use docker"
    assert "response_format" in _FakeLiteLLM.async_probe_calls[0]
    assert "response_format" in _FakeLiteLLM.async_completion_calls[0]


def test_async_structured_request_downgrades_only_when_unsupported() -> None:
    _FakeLiteLLM.response = _FakeResponse("use docker")

    fallback = asyncio.run(adapter.create_async_litellm_fallback("ollama/qwen2.5:14b-instruct"))

    assert asyncio.run(fallback("input")) == "use docker"
    assert "response_format" in _FakeLiteLLM.async_probe_calls[0]
    assert "response_format" not in _FakeLiteLLM.async_completion_calls[0]


def test_async_structured_provider_errors_remain_errors() -> None:
    _FakeLiteLLM.supports_schema = True
    _FakeLiteLLM.error = RuntimeError("connection failed")
    fallback = asyncio.run(adapter.create_async_litellm_fallback("ollama/qwen2.5:14b-instruct"))

    with pytest.raises(RuntimeError, match="connection failed"):
        asyncio.run(fallback("input"))


def test_structured_malformed_response_uses_existing_error() -> None:
    _FakeLiteLLM.supports_schema = True
    _FakeLiteLLM.response = _FakeResponse("not json")
    fallback = adapter.create_litellm_fallback("openai/gpt-4o-mini")

    with pytest.raises(InvalidFallbackResponseError):
        fallback("input")


def test_structured_helpers_reject_missing_schema_and_non_text_response() -> None:
    profile = FallbackProfile(
        system_prompt="",
        mode="structured",
        response_schema=None,
        abstention_sentinel=None,
    )
    with pytest.raises(RuntimeError, match="no response schema"):
        adapter._structured_response_format(profile)

    with pytest.raises(InvalidFallbackResponseError, match="content is not text"):
        adapter._structured_response_text(_FakeResponse(None))


def test_provider_errors_remain_errors() -> None:
    _FakeLiteLLM.error = RuntimeError("provider unavailable")
    fallback = adapter.create_litellm_fallback("openai/gpt-4o-mini")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        fallback("input")


def test_structured_provider_errors_remain_errors() -> None:
    _FakeLiteLLM.supports_schema = True
    _FakeLiteLLM.error = RuntimeError("connection failed")
    fallback = adapter.create_litellm_fallback("ollama/qwen2.5:14b-instruct")

    with pytest.raises(RuntimeError, match="connection failed"):
        fallback("input")


def test_structured_probe_propagates_non_capability_errors() -> None:
    _FakeLiteLLM.probe_error = RuntimeError("connection failed")

    with pytest.raises(RuntimeError, match="connection failed"):
        adapter.create_litellm_fallback("ollama/qwen2.5:14b-instruct")


def test_async_structured_probe_propagates_non_capability_errors() -> None:
    _FakeLiteLLM.probe_error = RuntimeError("connection failed")

    with pytest.raises(RuntimeError, match="connection failed"):
        asyncio.run(adapter.create_async_litellm_fallback("ollama/qwen2.5:14b-instruct"))


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
