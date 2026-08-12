from context_compiler.grammar import CanonicalDirective, InvalidDirectiveSyntax, decompose_directive


def test_consumed_grammar_helpers_are_importable_and_callable() -> None:
    assert callable(decompose_directive)


def test_consumed_core_grammar_result_types_match_expected_smoke_behavior() -> None:
    validated = decompose_directive("use docker")
    assert isinstance(validated, CanonicalDirective)
    assert validated.text == "use docker"

    assert decompose_directive("please use docker") is None

    assert isinstance(decompose_directive("clear state"), CanonicalDirective)
    assert decompose_directive("please clear state") is None

    compound = decompose_directive("use docker and prohibit peanuts")
    assert isinstance(compound, InvalidDirectiveSyntax)


def test_core_decompose_directive_now_exposes_invalid_syntax_diagnostics() -> None:
    invalid = decompose_directive("set premise to concise replies")
    assert isinstance(invalid, InvalidDirectiveSyntax)
