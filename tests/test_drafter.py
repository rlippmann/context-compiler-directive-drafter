import pytest
from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter import (
    DirectiveDrafter,
    DraftResult,
    NoDirective,
    UnknownDirective,
)
from context_compiler_directive_drafter import drafter as drafter_module


def _canonical(text: str):
    parsed = decompose_directive(text)
    assert parsed is not None
    return parsed


def test_no_directive_result_is_explicitly_fallback_eligible() -> None:
    drafted = DraftResult(source="heuristic", result=NoDirective(reason="reject.confident_non_directive"))

    assert drafter_module._is_fallback_eligible(drafted) is True


def test_unknown_result_is_explicitly_fallback_eligible() -> None:
    drafted = DraftResult(source="heuristic", result=UnknownDirective(reason="reject.directive_adjacent_unsafe"))

    assert drafter_module._is_fallback_eligible(drafted) is True


def test_canonical_directive_result_is_not_fallback_eligible() -> None:
    drafted = DraftResult(source="heuristic", result=_canonical("use docker"))

    assert drafter_module._is_fallback_eligible(drafted) is False


def test_fallback_callback_defaults_to_none() -> None:
    drafter = DirectiveDrafter()

    assert drafter.fallback is None


def test_fallback_callback_can_be_configured_at_construction() -> None:
    fallback = lambda _: DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))

    drafter = DirectiveDrafter(fallback=fallback)

    assert drafter.fallback is fallback


def test_fallback_callback_can_be_updated_after_construction() -> None:
    first = lambda _: DraftResult(source="llm", result=UnknownDirective(reason="first"))
    second = lambda _: DraftResult(source="llm", result=UnknownDirective(reason="second"))
    drafter = DirectiveDrafter(fallback=first)

    drafter.fallback = second

    assert drafter.fallback is second


def test_fallback_callback_can_be_cleared_after_construction() -> None:
    fallback = lambda _: DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))
    drafter = DirectiveDrafter(fallback=fallback)

    drafter.fallback = None

    assert drafter.fallback is None
    assert drafter.draft_directive("can you help with lunch?") == DraftResult(
        source="heuristic",
        result=NoDirective(reason="reject.confident_non_directive"),
    )


def test_fallback_is_used_when_heuristic_returns_no_directive() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> DraftResult:
        calls.append(user_input)
        return DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))

    drafter = DirectiveDrafter(fallback=fallback)

    result = drafter.draft_directive("can you help with lunch?")

    assert result == DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))
    assert calls == ["can you help with lunch?"]


def test_fallback_is_used_when_heuristic_abstains_with_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def heuristic(user_input: str) -> dict[str, str | None]:
        calls.append(f"heuristic:{user_input}")
        return {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }

    def fallback(user_input: str) -> DraftResult:
        calls.append(f"fallback:{user_input}")
        return DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))

    monkeypatch.setattr(drafter_module, "preprocess_heuristic", heuristic)
    drafter = DirectiveDrafter(fallback=fallback)
    result = drafter.draft_directive("use docker?")

    assert calls == ["heuristic:use docker?", "fallback:use docker?"]
    assert result == DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))


def test_fallback_is_not_used_when_heuristic_produces_a_directive() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> DraftResult:
        calls.append(user_input)
        return DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))

    drafter = DirectiveDrafter(fallback=fallback)

    result = drafter.draft_directive("set premise concise replies")

    assert result == DraftResult(
        source="heuristic",
        result=_canonical("set premise concise replies"),
    )
    assert calls == []


def test_fallback_canonical_directive_receives_the_same_validation_path() -> None:
    def fallback(user_input: str) -> DraftResult:
        assert user_input == "please make replies concise"
        return DraftResult(source="llm", result=_canonical("set premise concise replies"))

    drafter = DirectiveDrafter(fallback=fallback)

    result = drafter.draft_directive("please make replies concise")

    assert result == DraftResult(source="llm", result=_canonical("set premise concise replies"))


def test_no_fallback_preserves_existing_non_directive_behavior() -> None:
    drafter = DirectiveDrafter()

    result = drafter.draft_directive("can you help with lunch?")

    assert result == DraftResult(
        source="heuristic",
        result=NoDirective(reason="reject.confident_non_directive"),
    )


def test_drafting_does_not_require_engine_state_to_return_a_directive() -> None:
    drafter = DirectiveDrafter()

    result = drafter.draft_directive("set premise concise replies")

    assert result == DraftResult(
        source="heuristic",
        result=_canonical("set premise concise replies"),
    )


def test_fallback_no_directive_result_is_returned_unchanged() -> None:
    expected = DraftResult(source="llm", result=NoDirective(reason="llm_not_a_directive"))
    drafter = DirectiveDrafter(fallback=lambda _: expected)

    result = drafter.draft_directive("ordinary text")

    assert result == expected


def test_fallback_unknown_result_is_returned_unchanged() -> None:
    expected = DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))
    drafter = DirectiveDrafter(fallback=lambda _: expected)

    result = drafter.draft_directive("directive-like but unresolved")

    assert result == expected


def test_fallback_invalid_canonical_directive_text_returns_unknown_from_drafter() -> None:
    invalid = _canonical("use docker")
    object.__setattr__(invalid, "text", "please use docker")
    drafter = DirectiveDrafter(fallback=lambda _: DraftResult(source="llm", result=invalid))

    result = drafter.draft_directive("please use docker")

    assert result == DraftResult(
        source="llm",
        result=UnknownDirective(reason="invalid_canonical_directive"),
    )


def test_valid_fallback_directive_is_validated_before_returning() -> None:
    drafter = DirectiveDrafter(
        fallback=lambda _: DraftResult(source="llm", result=_canonical("use docker"))
    )

    result = drafter.draft_directive("please use docker")

    assert result == DraftResult(source="llm", result=_canonical("use docker"))


def test_heuristic_attempt_happens_before_fallback_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def heuristic(user_input: str) -> dict[str, str | None]:
        calls.append(f"heuristic:{user_input}")
        return {
            "outcome": "unknown",
            "directive": None,
            "reason": "reject.directive_adjacent_unsafe",
        }

    def fallback(user_input: str) -> DraftResult:
        calls.append(f"fallback:{user_input}")
        return DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))

    monkeypatch.setattr(drafter_module, "preprocess_heuristic", heuristic)
    drafter = DirectiveDrafter(fallback=fallback)

    result = drafter.draft_directive("can you help with lunch?")

    assert calls == [
        "heuristic:can you help with lunch?",
        "fallback:can you help with lunch?",
    ]
    assert result == DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))


def test_fallback_callback_is_skipped_when_heuristic_returns_valid_result() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> DraftResult:
        calls.append(user_input)
        return DraftResult(source="llm", result=UnknownDirective(reason="llm_ambiguous"))

    drafter = DirectiveDrafter(fallback=fallback)

    result = drafter.draft_directive("use docker")

    assert calls == []
    assert result == DraftResult(source="heuristic", result=_canonical("use docker"))
