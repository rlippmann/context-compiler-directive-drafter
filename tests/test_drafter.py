import asyncio
from dataclasses import FrozenInstanceError

import pytest
from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter import (
    PREPROCESSOR_NO_DIRECTIVE_SENTINEL,
    DirectiveDrafter,
    DraftResult,
    RejectedDirective,
    UnknownDirective,
)
from context_compiler_directive_drafter import drafter as drafter_module


def _canonical(text: str):
    parsed = decompose_directive(text)
    assert parsed is not None
    return parsed


def test_returned_draft_result_is_immutable() -> None:
    value = DirectiveDrafter().draft_directive("use docker")

    with pytest.raises(FrozenInstanceError):
        value.source = "changed"


@pytest.mark.parametrize("user_input", ["can you help with lunch?", "use docker?"])
def test_returned_noncanonical_results_are_immutable(user_input: str) -> None:
    value = DirectiveDrafter().draft_directive(user_input)

    assert isinstance(value.result, RejectedDirective | UnknownDirective)
    with pytest.raises(FrozenInstanceError):
        value.result.reason = "changed"


def test_draft_result_nested_public_result_is_immutable() -> None:
    result = DirectiveDrafter().draft_directive("can you help with lunch?")

    with pytest.raises(FrozenInstanceError):
        result.result.reason = "changed"


def test_independent_drafter_results_do_not_share_runtime_objects() -> None:
    drafter = DirectiveDrafter()

    first = drafter.draft_directive("can you help with lunch?")
    second = drafter.draft_directive("can you help with lunch?")

    assert first is not second
    assert isinstance(first.result, RejectedDirective)
    assert isinstance(second.result, RejectedDirective)
    assert first.result is not second.result


def test_fallback_callback_defaults_to_none() -> None:
    drafter = DirectiveDrafter()

    assert drafter.fallback is False
    assert drafter.async_fallback is False


@pytest.mark.parametrize(
    ("user_input", "reason"),
    [
        ("thanks for the help today", "non_directive"),
        ("use docker?", "non_directive"),
        ('he said "use docker".', "non_directive"),
        ("use podman instead of", "incomplete"),
        ("change premise to", "incomplete"),
        ("remove policy", "incomplete"),
        ("use docker and prohibit peanuts", "multiple_directives"),
    ],
)
def test_terminal_heuristic_results_use_public_rejection_taxonomy(
    user_input: str, reason: str
) -> None:
    result = DirectiveDrafter().draft_directive(user_input)

    assert result.source == "heuristic"
    assert isinstance(result.result, RejectedDirective)
    assert result.result.reason == reason


def test_semantic_uncertainty_is_the_only_fallback_eligible_result() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> str:
        calls.append(user_input)
        return "use docker"

    result = DirectiveDrafter(fallback=fallback).draft_directive("Could we maybe use uv later")

    assert isinstance(result.result, type(_canonical("use docker")))
    assert calls == ["Could we maybe use uv later"]


def test_provider_no_directive_sentinel_maps_to_public_terminal_reason() -> None:
    result = DirectiveDrafter(
        fallback=lambda _: f"  {PREPROCESSOR_NO_DIRECTIVE_SENTINEL}  "
    ).draft_directive("Could we maybe use uv later")

    assert result == DraftResult(
        source="fallback", result=RejectedDirective(reason="non_directive")
    )


def test_unrecognized_internal_terminal_reason_is_not_silently_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        drafter_module,
        "preprocess_heuristic",
        lambda _: {"outcome": "rejected", "directive": None, "reason": "unexpected"},
    )

    with pytest.raises(ValueError, match="Unsupported terminal heuristic reason"):
        DirectiveDrafter().draft_directive("input")


def test_fallback_callback_can_be_configured_at_construction() -> None:
    def fallback(_: str) -> str | None:
        return "use docker"

    drafter = DirectiveDrafter(fallback=fallback, fallback_source="llm")

    assert drafter.fallback is True


def test_fallback_callback_can_be_updated_after_construction() -> None:
    def first(_: str) -> str | None:
        return "use docker"

    def second(_: str) -> str | None:
        return "set premise concise replies"

    drafter = DirectiveDrafter(fallback=first, fallback_source="llm:first")

    drafter.configure_fallback(second, source="llm:second")

    assert drafter.fallback is True
    assert drafter.draft_directive("ordinary text") == DraftResult(
        source="llm:second",
        result=_canonical("set premise concise replies"),
    )


def test_fallback_callback_can_be_cleared_after_construction() -> None:
    def fallback(_: str) -> str | None:
        return "use docker"

    drafter = DirectiveDrafter(fallback=fallback, fallback_source="llm")

    drafter.clear_fallback()

    assert drafter.fallback is False
    assert drafter.draft_directive("can you help with lunch?") == DraftResult(
        source="heuristic",
        result=RejectedDirective(reason="non_directive"),
    )


def test_async_fallback_callback_can_be_configured_at_construction() -> None:
    async def async_fallback(_: str) -> str | None:
        return "use docker"

    drafter = DirectiveDrafter(async_fallback=async_fallback, async_fallback_source="llm")

    assert drafter.async_fallback is True


def test_async_fallback_callback_can_be_updated_after_construction() -> None:
    async def first(_: str) -> str | None:
        return "use docker"

    async def second(_: str) -> str | None:
        return "set premise concise replies"

    drafter = DirectiveDrafter(async_fallback=first, async_fallback_source="llm:first")

    drafter.configure_async_fallback(second, source="llm:second")

    assert drafter.async_fallback is True
    assert asyncio.run(drafter.async_draft_directive("ordinary text")) == DraftResult(
        source="llm:second",
        result=_canonical("set premise concise replies"),
    )


def test_async_fallback_callback_can_be_cleared_after_construction() -> None:
    async def async_fallback(_: str) -> str | None:
        return "use docker"

    drafter = DirectiveDrafter(async_fallback=async_fallback, async_fallback_source="llm")

    drafter.clear_async_fallback()

    assert drafter.async_fallback is False
    assert asyncio.run(drafter.async_draft_directive("can you help with lunch?")) == DraftResult(
        source="heuristic",
        result=RejectedDirective(reason="non_directive"),
    )


def test_fallback_is_not_used_when_heuristic_returns_no_directive() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> str | None:
        calls.append(user_input)
        return "use docker"

    drafter = DirectiveDrafter(fallback=fallback, fallback_source="llm")

    result = drafter.draft_directive("can you help with lunch?")

    assert result == DraftResult(
        source="heuristic",
        result=RejectedDirective(reason="non_directive"),
    )
    assert calls == []


def test_fallback_is_used_when_heuristic_abstains_with_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def heuristic(user_input: str) -> dict[str, object]:
        calls.append(f"heuristic:{user_input}")
        return {
            "outcome": "unknown",
            "directive": None,
            "reason": "semantic_uncertainty",
        }

    def fallback(user_input: str) -> str | None:
        calls.append(f"fallback:{user_input}")
        return "use docker"

    monkeypatch.setattr(drafter_module, "preprocess_heuristic", heuristic)
    drafter = DirectiveDrafter(fallback=fallback, fallback_source="llm")
    result = drafter.draft_directive("Could we maybe use uv later")

    assert calls == [
        "heuristic:Could we maybe use uv later",
        "fallback:Could we maybe use uv later",
    ]
    assert result == DraftResult(source="llm", result=_canonical("use docker"))


def test_fallback_is_not_used_when_heuristic_produces_a_directive() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> str | None:
        calls.append(user_input)
        return "use docker"

    drafter = DirectiveDrafter(fallback=fallback, fallback_source="llm")

    result = drafter.draft_directive("set premise concise replies")

    assert result == DraftResult(
        source="heuristic",
        result=_canonical("set premise concise replies"),
    )
    assert calls == []


def test_heuristic_canonical_directive_is_preserved_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical = _canonical("use docker")

    def heuristic(_: str) -> dict[str, object]:
        return {
            "outcome": "directive",
            "directive": canonical,
        }

    monkeypatch.setattr(drafter_module, "preprocess_heuristic", heuristic)

    drafter = DirectiveDrafter()

    assert drafter.draft_directive("use docker") == DraftResult(
        source="heuristic", result=canonical
    )


def test_fallback_canonical_directive_receives_the_same_validation_path() -> None:
    def fallback(user_input: str) -> str | None:
        assert user_input == "please make replies concise"
        return "set premise concise replies"

    drafter = DirectiveDrafter(fallback=fallback, fallback_source="llm")

    result = drafter.draft_directive("please make replies concise")

    assert result == DraftResult(source="llm", result=_canonical("set premise concise replies"))


def test_heuristic_directive_results_are_preserved_without_transformation() -> None:
    canonical = _canonical("set premise concise replies")

    result = drafter_module._heuristic_result_to_draft_result(
        {
            "outcome": "directive",
            "directive": canonical,
        }
    )

    assert result == DraftResult(source="heuristic", result=canonical)


def test_no_fallback_preserves_existing_non_directive_behavior() -> None:
    drafter = DirectiveDrafter()

    result = drafter.draft_directive("can you help with lunch?")

    assert result == DraftResult(
        source="heuristic",
        result=RejectedDirective(reason="non_directive"),
    )


def test_drafting_does_not_require_engine_state_to_return_a_directive() -> None:
    drafter = DirectiveDrafter()

    result = drafter.draft_directive("set premise concise replies")

    assert result == DraftResult(
        source="heuristic",
        result=_canonical("set premise concise replies"),
    )


def test_none_fallback_output_returns_no_directive_from_drafter() -> None:
    drafter = DirectiveDrafter(fallback=lambda _: None, fallback_source="llm")

    result = drafter.draft_directive("ordinary text")

    assert result == DraftResult(source="llm", result=RejectedDirective(reason="non_directive"))


def test_invalid_fallback_text_returns_unknown_from_drafter() -> None:
    drafter = DirectiveDrafter(fallback=lambda _: "please use docker", fallback_source="llm")

    result = drafter.draft_directive("directive-like but unresolved")

    assert result == DraftResult(
        source="llm",
        result=RejectedDirective(reason="invalid_candidate"),
    )


def test_valid_fallback_directive_is_validated_before_returning() -> None:
    drafter = DirectiveDrafter(fallback=lambda _: "use docker", fallback_source="llm")

    result = drafter.draft_directive("Could we maybe use uv later")

    assert result == DraftResult(source="llm", result=_canonical("use docker"))


def test_heuristic_attempt_happens_before_fallback_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def heuristic(user_input: str) -> dict[str, object]:
        calls.append(f"heuristic:{user_input}")
        return {
            "outcome": "unknown",
            "directive": None,
            "reason": "semantic_uncertainty",
        }

    def fallback(user_input: str) -> str | None:
        calls.append(f"fallback:{user_input}")
        return None

    monkeypatch.setattr(drafter_module, "preprocess_heuristic", heuristic)
    drafter = DirectiveDrafter(fallback=fallback, fallback_source="llm")

    result = drafter.draft_directive("can you help with lunch?")

    assert calls == [
        "heuristic:can you help with lunch?",
        "fallback:can you help with lunch?",
    ]
    assert result == DraftResult(source="llm", result=RejectedDirective(reason="non_directive"))


def test_fallback_callback_is_skipped_when_heuristic_returns_valid_result() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> str | None:
        calls.append(user_input)
        return "use docker"

    drafter = DirectiveDrafter(fallback=fallback, fallback_source="llm")

    result = drafter.draft_directive("use docker")

    assert calls == []
    assert result == DraftResult(source="heuristic", result=_canonical("use docker"))


def test_async_heuristic_canonical_directive_skips_fallback() -> None:
    calls: list[str] = []

    async def async_fallback(user_input: str) -> str | None:
        calls.append(user_input)
        return "use docker"

    drafter = DirectiveDrafter(async_fallback=async_fallback, async_fallback_source="llm")

    result = asyncio.run(drafter.async_draft_directive("set premise concise replies"))

    assert calls == []
    assert result == DraftResult(
        source="heuristic",
        result=_canonical("set premise concise replies"),
    )


def test_async_no_directive_does_not_invoke_async_fallback() -> None:
    calls: list[str] = []

    async def async_fallback(user_input: str) -> str | None:
        calls.append(user_input)
        return "use docker"

    drafter = DirectiveDrafter(async_fallback=async_fallback, async_fallback_source="llm")

    result = asyncio.run(drafter.async_draft_directive("can you help with lunch?"))

    assert calls == []
    assert result == DraftResult(
        source="heuristic",
        result=RejectedDirective(reason="non_directive"),
    )


def test_async_unknown_directive_invokes_async_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def heuristic(user_input: str) -> dict[str, object]:
        calls.append(f"heuristic:{user_input}")
        return {
            "outcome": "unknown",
            "directive": None,
            "reason": "semantic_uncertainty",
        }

    async def async_fallback(user_input: str) -> str | None:
        calls.append(f"fallback:{user_input}")
        return "use docker"

    monkeypatch.setattr(drafter_module, "preprocess_heuristic", heuristic)
    drafter = DirectiveDrafter(async_fallback=async_fallback, async_fallback_source="llm")

    result = asyncio.run(drafter.async_draft_directive("Could we maybe use uv later"))

    assert calls == [
        "heuristic:Could we maybe use uv later",
        "fallback:Could we maybe use uv later",
    ]
    assert result == DraftResult(source="llm", result=_canonical("use docker"))


def test_missing_async_fallback_preserves_heuristic_only_behavior() -> None:
    drafter = DirectiveDrafter()

    result = asyncio.run(drafter.async_draft_directive("can you help with lunch?"))

    assert result == DraftResult(
        source="heuristic",
        result=RejectedDirective(reason="non_directive"),
    )


def test_async_fallback_canonical_directive_receives_the_same_validation_path() -> None:
    async def async_fallback(user_input: str) -> str | None:
        assert user_input == "please make replies concise"
        return "set premise concise replies"

    drafter = DirectiveDrafter(async_fallback=async_fallback, async_fallback_source="llm")

    result = asyncio.run(drafter.async_draft_directive("please make replies concise"))

    assert result == DraftResult(source="llm", result=_canonical("set premise concise replies"))


def test_async_none_fallback_output_returns_no_directive_from_drafter() -> None:
    async def async_fallback(_: str) -> str | None:
        return None

    drafter = DirectiveDrafter(async_fallback=async_fallback, async_fallback_source="llm")

    result = asyncio.run(drafter.async_draft_directive("ordinary text"))

    assert result == DraftResult(source="llm", result=RejectedDirective(reason="non_directive"))


def test_async_invalid_fallback_text_returns_unknown_from_drafter() -> None:
    async def async_fallback(_: str) -> str | None:
        return "please use docker"

    drafter = DirectiveDrafter(async_fallback=async_fallback, async_fallback_source="llm")

    result = asyncio.run(drafter.async_draft_directive("directive-like but unresolved"))

    assert result == DraftResult(
        source="llm",
        result=RejectedDirective(reason="invalid_candidate"),
    )
