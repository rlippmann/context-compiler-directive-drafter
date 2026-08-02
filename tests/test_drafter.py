from context_compiler.grammar import CanonicalDirective, DirectiveKind
from context_compiler import create_engine
from types import MappingProxyType

from context_compiler_directive_drafter import DirectiveDrafter, DraftResult
import context_compiler_directive_drafter.drafter as drafter_module


def test_fallback_is_used_when_heuristic_does_not_produce_a_directive() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> DraftResult:
        calls.append(user_input)
        return DraftResult(outcome="unknown", directive=None)

    drafter = DirectiveDrafter(fallback=fallback)
    engine = create_engine({"premise": None, "policies": {}, "version": 2})

    result = drafter.draft_directive("can you help with lunch?", engine)

    assert result == DraftResult(outcome="unknown", directive=None)
    assert calls == ["can you help with lunch?"]


def test_fallback_is_not_used_when_heuristic_produces_a_directive() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> DraftResult:
        calls.append(user_input)
        return DraftResult(outcome="unknown", directive=None)

    drafter = DirectiveDrafter(fallback=fallback)
    engine = create_engine({"premise": None, "policies": {}, "version": 2})

    result = drafter.draft_directive("set premise concise replies", engine)

    assert result == DraftResult(outcome="directive", directive="set premise concise replies")
    assert calls == []


def test_fallback_directive_receives_the_same_refinement_path() -> None:
    def fallback(user_input: str) -> DraftResult:
        assert user_input == "please make replies concise"
        return DraftResult(outcome="directive", directive="set premise concise replies")

    drafter = DirectiveDrafter(fallback=fallback)
    engine = create_engine({"premise": "existing premise", "policies": {}, "version": 2})

    result = drafter.draft_directive("please make replies concise", engine)

    assert result == DraftResult(outcome="directive", directive="change premise to concise replies")


def test_no_fallback_preserves_existing_non_directive_behavior() -> None:
    drafter = DirectiveDrafter()
    engine = create_engine({"premise": None, "policies": {}, "version": 2})

    result = drafter.draft_directive("can you help with lunch?", engine)

    assert result == DraftResult(outcome="no_directive", directive=None)


def test_refinement_happens_once_when_heuristic_succeeds(monkeypatch) -> None:
    refined_calls: list[str] = []

    def fake_refine(directive: CanonicalDirective, engine) -> CanonicalDirective:
        refined_calls.append(directive.text)
        return directive

    monkeypatch.setattr(drafter_module, "refine_directive", fake_refine)

    drafter = DirectiveDrafter(fallback=lambda _: DraftResult(outcome="unknown", directive=None))
    engine = create_engine({"premise": None, "policies": {}, "version": 2})

    result = drafter.draft_directive("set premise concise replies", engine)

    assert result == DraftResult(outcome="directive", directive="set premise concise replies")
    assert refined_calls == ["set premise concise replies"]


def test_refinement_happens_once_after_fallback_selection(monkeypatch) -> None:
    refined_calls: list[str] = []

    def fake_refine(directive: CanonicalDirective, engine) -> CanonicalDirective:
        refined_calls.append(directive.text)
        return CanonicalDirective(
            text="change premise to concise replies",
            kind=DirectiveKind.CHANGE_PREMISE,
            operands=MappingProxyType({"value": "concise replies"}),
        )

    monkeypatch.setattr(drafter_module, "refine_directive", fake_refine)

    drafter = DirectiveDrafter(
        fallback=lambda _: DraftResult(outcome="directive", directive="set premise concise replies")
    )
    engine = create_engine({"premise": "existing premise", "policies": {}, "version": 2})

    result = drafter.draft_directive("please make replies concise", engine)

    assert result == DraftResult(outcome="directive", directive="change premise to concise replies")
    assert refined_calls == ["set premise concise replies"]


def test_fallback_non_directive_result_is_returned_unchanged() -> None:
    expected = DraftResult(outcome="no_directive", directive=None)
    drafter = DirectiveDrafter(fallback=lambda _: expected)
    engine = create_engine({"premise": None, "policies": {}, "version": 2})

    result = drafter.draft_directive("ordinary text", engine)

    assert result == expected


def test_fallback_unknown_result_is_returned_unchanged_even_if_directive_is_missing() -> None:
    expected = DraftResult(outcome="unknown", directive=None)
    drafter = DirectiveDrafter(fallback=lambda _: expected)
    engine = create_engine({"premise": None, "policies": {}, "version": 2})

    result = drafter.draft_directive("directive-like but unresolved", engine)

    assert result == expected
