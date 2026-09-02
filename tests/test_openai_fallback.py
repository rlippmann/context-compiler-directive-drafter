import asyncio
import subprocess
import sys
from types import SimpleNamespace

import pytest

from context_compiler_directive_drafter import (
    DirectiveDrafter,
    DraftResult,
    RejectedDirective,
    create_async_openai_fallback,
    create_openai_fallback,
)
from context_compiler_directive_drafter.constants import NO_DIRECTIVE
from context_compiler_directive_drafter.drafter import InvalidFallbackResponseError
from context_compiler_directive_drafter.fallbacks import get_fallback_profile
from context_compiler_directive_drafter.fallbacks import openai as adapter


class _FakeResponse:
    def __init__(self, content: str | None) -> None:
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]


class _FakeCompletions:
    def __init__(
        self,
        response: _FakeResponse,
        structured_probe_error: Exception | None,
        structured_probe_response: _FakeResponse,
    ) -> None:
        self.response = response
        self.structured_probe_error = structured_probe_error
        self.structured_probe_response = structured_probe_response
        self.probe_consumed = False
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> _FakeResponse:
        self.calls.append(kwargs)
        if "response_format" in kwargs and self.structured_probe_error is not None:
            raise self.structured_probe_error
        if "response_format" in kwargs and not self.probe_consumed:
            self.probe_consumed = True
            return self.structured_probe_response
        return self.response


class _FakeAsyncCompletions(_FakeCompletions):
    async def create(self, **kwargs: object) -> _FakeResponse:
        self.calls.append(kwargs)
        if "response_format" in kwargs and self.structured_probe_error is not None:
            raise self.structured_probe_error
        if "response_format" in kwargs and not self.probe_consumed:
            self.probe_consumed = True
            return self.structured_probe_response
        return self.response


class _FakeOpenAI:
    instances: list["_FakeOpenAI"] = []
    structured_probe_error: Exception | None = RuntimeError("response_format is not supported")
    structured_probe_response = _FakeResponse('{"ok":true}')

    def __init__(self, **kwargs: str) -> None:
        self.init_kwargs = kwargs
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(
                _FakeResponse("use docker"),
                self.structured_probe_error,
                self.structured_probe_response,
            )
        )
        self.instances.append(self)


class _FakeAsyncOpenAI:
    instances: list["_FakeAsyncOpenAI"] = []
    structured_probe_error: Exception | None = RuntimeError("response_format is not supported")
    structured_probe_response = _FakeResponse('{"ok":true}')

    def __init__(self, **kwargs: str) -> None:
        self.init_kwargs = kwargs
        self.chat = SimpleNamespace(
            completions=_FakeAsyncCompletions(
                _FakeResponse("use podman"),
                self.structured_probe_error,
                self.structured_probe_response,
            )
        )
        self.instances.append(self)


@pytest.fixture(autouse=True)
def _reset_fake_clients() -> None:
    _FakeOpenAI.instances.clear()
    _FakeAsyncOpenAI.instances.clear()
    _FakeOpenAI.structured_probe_error = RuntimeError("response_format is not supported")
    _FakeAsyncOpenAI.structured_probe_error = RuntimeError("response_format is not supported")
    _FakeOpenAI.structured_probe_response = _FakeResponse('{"ok":true}')
    _FakeAsyncOpenAI.structured_probe_response = _FakeResponse('{"ok":true}')


def _patch_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "_load_openai_clients", lambda: (_FakeOpenAI, _FakeAsyncOpenAI))


def _enable_structured_output() -> None:
    _FakeOpenAI.structured_probe_error = None
    _FakeAsyncOpenAI.structured_probe_error = None


def test_sync_fallback_forwards_configuration_request_and_selects_free_text_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = create_openai_fallback(
        model="compatible-model",
        api_key="test-key",
        base_url="https://provider.example/v1",
        request_kwargs={
            "temperature": 0,
            "timeout": 12,
            "response_format": {"type": "json_object"},
        },
    )

    assert fallback("Use Docker unchanged") == "use docker"
    client = _FakeOpenAI.instances[0]
    assert client.init_kwargs == {
        "api_key": "test-key",
        "base_url": "https://provider.example/v1",
    }
    assert client.chat.completions.calls[-1:] == [
        {
            "temperature": 0,
            "timeout": 12,
            "model": "compatible-model",
            "messages": [
                {"role": "system", "content": get_fallback_profile().system_prompt},
                {"role": "user", "content": "Use Docker unchanged"},
            ],
        }
    ]


def test_sync_fallback_omits_unset_client_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = create_openai_fallback(model="compatible-model")

    assert fallback("input") == "use docker"
    assert _FakeOpenAI.instances[0].init_kwargs == {}


def test_sync_probe_downgrades_only_clear_unsupported_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = create_openai_fallback(model="compatible-model")
    client = _FakeOpenAI.instances[0]
    client.chat.completions.response = _FakeResponse("use docker")
    client.chat.completions.structured_probe_error = None

    assert fallback("input") == "use docker"
    assert "response_format" not in client.chat.completions.calls[-1]


def test_sync_probe_downgrades_successful_but_nonconforming_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    _FakeOpenAI.structured_probe_response = _FakeResponse("ordinary text")
    fallback = create_openai_fallback(model="compatible-model")
    client = _FakeOpenAI.instances[0]
    client.chat.completions.response = _FakeResponse("use docker")

    assert fallback("input") == "use docker"
    assert "response_format" not in client.chat.completions.calls[-1]


def test_sync_probe_downgrades_successful_non_text_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    _FakeOpenAI.structured_probe_response = _FakeResponse(None)
    fallback = create_openai_fallback(model="compatible-model")
    client = _FakeOpenAI.instances[0]
    client.chat.completions.response = _FakeResponse("use docker")

    assert fallback("input") == "use docker"
    assert "response_format" not in client.chat.completions.calls[-1]


def test_sync_probe_propagates_unknown_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_clients(monkeypatch)
    _FakeOpenAI.structured_probe_error = RuntimeError("connection failed")

    with pytest.raises(RuntimeError, match="connection failed"):
        create_openai_fallback(model="compatible-model")


def test_sync_fallback_normalizes_no_directive_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = create_openai_fallback(model="compatible-model")
    _FakeOpenAI.instances[0].chat.completions.response = _FakeResponse(f"  {NO_DIRECTIVE} \n")

    assert fallback("input") is None


def test_sync_fallback_preserves_canonical_and_invalid_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = create_openai_fallback(model="compatible-model")
    completions = _FakeOpenAI.instances[0].chat.completions

    completions.response = _FakeResponse("use docker")
    assert fallback("input") == "use docker"

    completions.response = _FakeResponse("not a directive")
    assert fallback("input") == "not a directive"


def test_sync_structured_fallback_selects_prompt_and_parses_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    fallback = create_openai_fallback(model="compatible-model")
    client = _FakeOpenAI.instances[0]
    client.chat.completions.response = _FakeResponse(
        '{"classification":"directive","output":"use docker"}'
    )

    assert fallback("input") == "use docker"
    call = client.chat.completions.calls[-1]
    assert call["messages"][0] == {
        "role": "system",
        "content": get_fallback_profile(structured_output=True).system_prompt,
    }
    assert call["response_format"] == adapter._STRUCTURED_RESPONSE_FORMAT


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"classification":"directive","output":null}',
        '{"classification":"rejected","output":"use docker"}',
        '{"classification":"rejected","output":null,"extra":false}',
    ],
)
def test_sync_structured_fallback_rejects_invalid_envelopes(
    monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    fallback = create_openai_fallback(model="compatible-model")
    _FakeOpenAI.instances[0].chat.completions.response = _FakeResponse(content)

    with pytest.raises(InvalidFallbackResponseError):
        fallback("input")


def test_sync_structured_fallback_rejects_non_text_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    fallback = create_openai_fallback(model="compatible-model")
    _FakeOpenAI.instances[0].chat.completions.response = _FakeResponse(None)

    with pytest.raises(InvalidFallbackResponseError):
        fallback("input")


def test_drafter_maps_invalid_structured_response_to_invalid_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    fallback = create_openai_fallback(model="compatible-model")
    _FakeOpenAI.instances[0].chat.completions.response = _FakeResponse("not json")
    drafter = DirectiveDrafter(fallback=fallback, fallback_source="openai-compatible")

    result = drafter.draft_directive("Could we maybe use uv later")

    assert result == DraftResult(
        source="openai-compatible",
        result=RejectedDirective(reason="invalid_candidate"),
    )


def test_async_fallback_forwards_configuration_and_returns_raw_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = asyncio.run(
        create_async_openai_fallback(
            model="compatible-model",
            api_key="test-key",
            base_url="http://localhost:11434/v1",
            request_kwargs={"temperature": 0.2},
        )
    )

    assert asyncio.run(fallback("original input")) == "use podman"
    client = _FakeAsyncOpenAI.instances[0]
    assert client.init_kwargs == {
        "api_key": "test-key",
        "base_url": "http://localhost:11434/v1",
    }
    assert client.chat.completions.calls[-1]["model"] == "compatible-model"
    assert client.chat.completions.calls[-1]["temperature"] == 0.2
    assert client.chat.completions.calls[-1]["messages"] == [
        {"role": "system", "content": get_fallback_profile().system_prompt},
        {"role": "user", "content": "original input"},
    ]


def test_async_fallback_normalizes_no_directive_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = asyncio.run(create_async_openai_fallback(model="compatible-model"))
    _FakeAsyncOpenAI.instances[0].chat.completions.response = _FakeResponse(f"\n{NO_DIRECTIVE}\n")

    assert asyncio.run(fallback("input")) is None


def test_async_probe_downgrades_only_clear_unsupported_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = asyncio.run(create_async_openai_fallback(model="compatible-model"))
    client = _FakeAsyncOpenAI.instances[0]
    client.chat.completions.response = _FakeResponse("use podman")
    client.chat.completions.structured_probe_error = None

    assert asyncio.run(fallback("input")) == "use podman"
    assert "response_format" not in client.chat.completions.calls[-1]


def test_async_probe_downgrades_successful_but_nonconforming_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    _FakeAsyncOpenAI.structured_probe_response = _FakeResponse("ordinary text")
    fallback = asyncio.run(create_async_openai_fallback(model="compatible-model"))
    client = _FakeAsyncOpenAI.instances[0]
    client.chat.completions.response = _FakeResponse("use podman")

    assert asyncio.run(fallback("input")) == "use podman"
    assert "response_format" not in client.chat.completions.calls[-1]


def test_async_probe_propagates_unknown_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_clients(monkeypatch)
    _FakeAsyncOpenAI.structured_probe_error = RuntimeError("connection failed")

    with pytest.raises(RuntimeError, match="connection failed"):
        asyncio.run(create_async_openai_fallback(model="compatible-model"))


def test_async_structured_fallback_maps_rejection_and_uses_structured_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    fallback = asyncio.run(create_async_openai_fallback(model="compatible-model"))
    client = _FakeAsyncOpenAI.instances[0]
    client.chat.completions.response = _FakeResponse('{"classification":"rejected","output":null}')

    assert asyncio.run(fallback("input")) is None
    call = client.chat.completions.calls[-1]
    assert call["messages"][0] == {
        "role": "system",
        "content": get_fallback_profile(structured_output=True).system_prompt,
    }
    assert call["response_format"] == adapter._STRUCTURED_RESPONSE_FORMAT


def test_async_drafter_maps_invalid_structured_response_to_invalid_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    _enable_structured_output()
    fallback = asyncio.run(create_async_openai_fallback(model="compatible-model"))
    _FakeAsyncOpenAI.instances[0].chat.completions.response = _FakeResponse("not json")
    drafter = DirectiveDrafter(async_fallback=fallback, async_fallback_source="openai-compatible")

    result = asyncio.run(drafter.async_draft_directive("Could we maybe use uv later"))

    assert result == DraftResult(
        source="openai-compatible",
        result=RejectedDirective(reason="invalid_candidate"),
    )


def test_missing_optional_dependency_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def import_without_openai(name: str) -> object:
        if name == "openai":
            raise ImportError("openai is unavailable")
        raise AssertionError(f"unexpected optional import: {name}")

    monkeypatch.setattr(adapter, "import_module", import_without_openai)

    with pytest.raises(RuntimeError, match=r"pip install .*\[openai\]"):
        create_openai_fallback(model="compatible-model")


def test_optional_dependency_loader_returns_sdk_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(AsyncOpenAI=_FakeAsyncOpenAI, OpenAI=_FakeOpenAI),
    )

    assert adapter._load_openai_clients() == (_FakeOpenAI, _FakeAsyncOpenAI)


def test_normal_package_import_does_not_require_optional_dependency() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import context_compiler_directive_drafter"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_callback_works_with_existing_drafter_fallback_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    drafter = DirectiveDrafter(
        fallback=create_openai_fallback(model="compatible-model"),
        fallback_source="openai-compatible",
    )

    result = drafter.draft_directive("Could we maybe use uv later")

    assert result.source == "openai-compatible"
    assert result.result.text == "use docker"


def test_no_directive_sentinel_produces_drafter_no_directive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = create_openai_fallback(model="compatible-model")
    _FakeOpenAI.instances[0].chat.completions.response = _FakeResponse(NO_DIRECTIVE)
    drafter = DirectiveDrafter(
        fallback=fallback,
        fallback_source="openai-compatible",
    )

    result = drafter.draft_directive("Could we maybe use uv later")

    assert result == DraftResult(
        source="openai-compatible",
        result=RejectedDirective(reason="non_directive"),
    )
