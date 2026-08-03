from context_compiler.grammar import (
    contains_multiple_canonical_directives,
    is_canonical_directive,
    validate_directive,
)


def test_consumed_grammar_helpers_are_importable_and_callable() -> None:
    assert callable(contains_multiple_canonical_directives)
    assert callable(validate_directive)
    assert callable(is_canonical_directive)


def test_consumed_grammar_helpers_match_expected_smoke_behavior() -> None:
    validated = validate_directive("use docker")
    assert validated is not None
    assert validated.text == "use docker"

    assert validate_directive("please use docker") is None

    assert is_canonical_directive("clear state")
    assert not is_canonical_directive("please clear state")

    assert contains_multiple_canonical_directives("use docker and prohibit peanuts")
    assert not contains_multiple_canonical_directives("use docker")
