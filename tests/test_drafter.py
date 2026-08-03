from context_compiler_directive_drafter import DirectiveDrafter, DraftResult


def test_fallback_is_used_when_heuristic_does_not_produce_a_directive() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> DraftResult:
        calls.append(user_input)
        return DraftResult(outcome="unknown", directive=None)

    drafter = DirectiveDrafter(fallback=fallback)

    result = drafter.draft_directive("can you help with lunch?")

    assert result == DraftResult(outcome="unknown", directive=None)
    assert calls == ["can you help with lunch?"]


def test_fallback_is_not_used_when_heuristic_produces_a_directive() -> None:
    calls: list[str] = []

    def fallback(user_input: str) -> DraftResult:
        calls.append(user_input)
        return DraftResult(outcome="unknown", directive=None)

    drafter = DirectiveDrafter(fallback=fallback)

    result = drafter.draft_directive("set premise concise replies")

    assert result == DraftResult(outcome="directive", directive="set premise concise replies")
    assert calls == []


def test_fallback_directive_receives_the_same_validation_path() -> None:
    def fallback(user_input: str) -> DraftResult:
        assert user_input == "please make replies concise"
        return DraftResult(outcome="directive", directive="set premise concise replies")

    drafter = DirectiveDrafter(fallback=fallback)

    result = drafter.draft_directive("please make replies concise")

    assert result == DraftResult(outcome="directive", directive="set premise concise replies")


def test_no_fallback_preserves_existing_non_directive_behavior() -> None:
    drafter = DirectiveDrafter()

    result = drafter.draft_directive("can you help with lunch?")

    assert result == DraftResult(outcome="no_directive", directive=None)


def test_drafting_does_not_require_engine_state_to_return_a_directive() -> None:
    drafter = DirectiveDrafter()

    result = drafter.draft_directive("set premise concise replies")

    assert result == DraftResult(outcome="directive", directive="set premise concise replies")


def test_fallback_non_directive_result_is_returned_unchanged() -> None:
    expected = DraftResult(outcome="no_directive", directive=None)
    drafter = DirectiveDrafter(fallback=lambda _: expected)

    result = drafter.draft_directive("ordinary text")

    assert result == expected


def test_fallback_unknown_result_is_returned_unchanged_even_if_directive_is_missing() -> None:
    expected = DraftResult(outcome="unknown", directive=None)
    drafter = DirectiveDrafter(fallback=lambda _: expected)

    result = drafter.draft_directive("directive-like but unresolved")

    assert result == expected


def test_invalid_fallback_directive_returns_unknown() -> None:
    drafter = DirectiveDrafter(
        fallback=lambda _: DraftResult(outcome="directive", directive="please use docker")
    )

    result = drafter.draft_directive("please use docker")

    assert result == DraftResult(outcome="unknown", directive=None)


def test_valid_fallback_directive_is_validated_before_returning() -> None:
    drafter = DirectiveDrafter(
        fallback=lambda _: DraftResult(outcome="directive", directive="use docker")
    )

    result = drafter.draft_directive("please use docker")

    assert result == DraftResult(outcome="directive", directive="use docker")
