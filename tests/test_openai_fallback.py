import asyncio
import subprocess
import sys
from types import SimpleNamespace

import pytest

from context_compiler_directive_drafter import (
    PREPROCESSOR_NO_DIRECTIVE_SENTINEL,
    DirectiveDrafter,
    DraftResult,
    RejectedDirective,
    create_async_openai_fallback,
    create_openai_fallback,
)
from context_compiler_directive_drafter import openai_fallback as adapter


class _FakeResponse:
    def __init__(self, content: str | None) -> None:
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]


class _FakeCompletions:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> _FakeResponse:
        self.calls.append(kwargs)
        return self.response


class _FakeAsyncCompletions(_FakeCompletions):
    async def create(self, **kwargs: object) -> _FakeResponse:
        self.calls.append(kwargs)
        return self.response


class _FakeOpenAI:
    instances: list["_FakeOpenAI"] = []

    def __init__(self, **kwargs: str) -> None:
        self.init_kwargs = kwargs
        self.chat = SimpleNamespace(completions=_FakeCompletions(_FakeResponse("use docker")))
        self.instances.append(self)


class _FakeAsyncOpenAI:
    instances: list["_FakeAsyncOpenAI"] = []

    def __init__(self, **kwargs: str) -> None:
        self.init_kwargs = kwargs
        self.chat = SimpleNamespace(completions=_FakeAsyncCompletions(_FakeResponse("use podman")))
        self.instances.append(self)


@pytest.fixture(autouse=True)
def _reset_fake_clients() -> None:
    _FakeOpenAI.instances.clear()
    _FakeAsyncOpenAI.instances.clear()


def _patch_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "_load_openai_clients", lambda: (_FakeOpenAI, _FakeAsyncOpenAI))


def test_sync_fallback_forwards_configuration_request_and_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    monkeypatch.setattr(adapter, "get_converter_prompt", lambda: "converter instructions")

    fallback = create_openai_fallback(
        model="compatible-model",
        api_key="test-key",
        base_url="https://provider.example/v1",
        request_kwargs={"temperature": 0, "timeout": 12},
    )

    assert fallback("Use Docker unchanged") == "use docker"
    client = _FakeOpenAI.instances[0]
    assert client.init_kwargs == {
        "api_key": "test-key",
        "base_url": "https://provider.example/v1",
    }
    assert client.chat.completions.calls == [
        {
            "temperature": 0,
            "timeout": 12,
            "model": "compatible-model",
            "messages": [
                {"role": "system", "content": "converter instructions"},
                {"role": "user", "content": "Use Docker unchanged"},
            ],
        }
    ]


def test_sync_fallback_omits_unset_client_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    monkeypatch.setattr(adapter, "get_converter_prompt", lambda: "prompt")

    fallback = create_openai_fallback(model="compatible-model")

    assert fallback("input") == "use docker"
    assert _FakeOpenAI.instances[0].init_kwargs == {}


def test_sync_fallback_normalizes_no_directive_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = create_openai_fallback(model="compatible-model")
    _FakeOpenAI.instances[0].chat.completions.response = _FakeResponse(
        f"  {PREPROCESSOR_NO_DIRECTIVE_SENTINEL} \n"
    )

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


def test_async_fallback_forwards_configuration_and_returns_raw_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    monkeypatch.setattr(adapter, "get_converter_prompt", lambda: "async prompt")

    fallback = create_async_openai_fallback(
        model="compatible-model",
        api_key="test-key",
        base_url="http://localhost:11434/v1",
        request_kwargs={"temperature": 0.2},
    )

    assert asyncio.run(fallback("original input")) == "use podman"
    client = _FakeAsyncOpenAI.instances[0]
    assert client.init_kwargs == {
        "api_key": "test-key",
        "base_url": "http://localhost:11434/v1",
    }
    assert client.chat.completions.calls[0]["model"] == "compatible-model"
    assert client.chat.completions.calls[0]["temperature"] == 0.2
    assert client.chat.completions.calls[0]["messages"] == [
        {"role": "system", "content": "async prompt"},
        {"role": "user", "content": "original input"},
    ]


def test_async_fallback_normalizes_no_directive_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_clients(monkeypatch)
    fallback = create_async_openai_fallback(model="compatible-model")
    _FakeAsyncOpenAI.instances[0].chat.completions.response = _FakeResponse(
        f"\n{PREPROCESSOR_NO_DIRECTIVE_SENTINEL}\n"
    )

    assert asyncio.run(fallback("input")) is None


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
    monkeypatch.setattr(adapter, "get_converter_prompt", lambda: "prompt")

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
    _FakeOpenAI.instances[0].chat.completions.response = _FakeResponse(
        PREPROCESSOR_NO_DIRECTIVE_SENTINEL
    )
    drafter = DirectiveDrafter(
        fallback=fallback,
        fallback_source="openai-compatible",
    )

    result = drafter.draft_directive("Could we maybe use uv later")

    assert result == DraftResult(
        source="openai-compatible",
        result=RejectedDirective(reason="fallback_no_candidate"),
    )
