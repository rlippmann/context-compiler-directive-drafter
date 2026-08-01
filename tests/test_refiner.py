from context_compiler import create_engine
from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter import refine_directive


def _refine_with_engine(
    directive_text: str,
    prelude: list[str],
):
    engine = create_engine()
    for item in prelude:
        engine.step(item)

    before = engine.state
    directive = decompose_directive(directive_text)
    assert directive is not None

    original_step = engine.step

    def _unexpected_step(_: str) -> object:
        raise AssertionError("refine_directive() must not invoke engine.step()")

    engine.step = _unexpected_step  # type: ignore[method-assign]
    try:
        refined = refine_directive(directive, engine)
    finally:
        engine.step = original_step  # type: ignore[method-assign]

    assert engine.state == before
    return refined, directive, before


def test_refine_directive_rewrites_set_premise_to_change_premise_when_premise_exists() -> None:
    refined, _, _ = _refine_with_engine(
        "set premise concise replies",
        ["set premise existing premise"],
    )

    assert refined == decompose_directive("change premise to concise replies")


def test_refine_directive_rewrites_change_premise_to_set_premise_when_premise_missing() -> None:
    refined, _, _ = _refine_with_engine(
        "change premise to concise replies",
        [],
    )

    assert refined == decompose_directive("set premise concise replies")


def test_refine_directive_leaves_set_premise_unchanged_when_premise_missing() -> None:
    refined, directive, _ = _refine_with_engine("set premise concise replies", [])

    assert refined == directive


def test_refine_directive_leaves_change_premise_unchanged_when_premise_exists() -> None:
    refined, directive, _ = _refine_with_engine(
        "change premise to concise replies",
        ["set premise existing premise"],
    )

    assert refined == directive


def test_refine_directive_leaves_unrelated_directives_unchanged() -> None:
    refined, directive, _ = _refine_with_engine(
        "prohibit kubectl",
        [
            "set premise concise replies",
            "use docker",
            "prohibit pytest",
        ],
    )

    assert refined == directive


def test_refine_directive_preserves_populated_authoritative_engine_state() -> None:
    _, _, before = _refine_with_engine(
        "set premise concise replies",
        [
            "set premise existing premise",
            "use docker",
            "prohibit pytest",
        ],
    )

    assert before == {
        "premise": "existing premise",
        "policies": {
            "docker": "use",
            "pytest": "prohibit",
        },
        "version": 2,
    }
