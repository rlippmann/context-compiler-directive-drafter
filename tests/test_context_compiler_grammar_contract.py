from context_compiler.grammar import (
    contains_multiple_canonical_directives,
    validate_directive,
)


def test_consumed_grammar_helpers_are_importable_and_callable() -> None:
    assert callable(contains_multiple_canonical_directives)
    assert callable(validate_directive)


def test_consumed_grammar_helpers_match_expected_smoke_behavior() -> None:
    validated = validate_directive("use docker")
    assert validated is not None
    assert validated.text == "use docker"

    assert validate_directive("please use docker") is None

    assert validate_directive("clear state") is not None
    assert validate_directive("please clear state") is None

    assert contains_multiple_canonical_directives("use docker and prohibit peanuts")
    assert not contains_multiple_canonical_directives("use docker")
