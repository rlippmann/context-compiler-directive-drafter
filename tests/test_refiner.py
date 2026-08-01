from context_compiler import create_engine
from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter import refine_directive


def _assert_refinement_preserves_engine_state(directive_text: str, prelude: list[str]) -> None:
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
        assert refine_directive(directive, engine) == directive
    finally:
        engine.step = original_step  # type: ignore[method-assign]

    assert engine.state == before


def test_refine_directive_returns_same_canonical_directive_for_no_op_placeholder() -> None:
    _assert_refinement_preserves_engine_state("set premise concise replies", [])


def test_refine_directive_accepts_replacement_directive_without_rewriting_yet() -> None:
    _assert_refinement_preserves_engine_state(
        "use podman instead of docker",
        ["use docker"],
    )


def test_refine_directive_preserves_populated_authoritative_engine_state() -> None:
    _assert_refinement_preserves_engine_state(
        "prohibit kubectl",
        [
            "set premise concise replies",
            "use docker",
            "prohibit pytest",
        ],
    )
