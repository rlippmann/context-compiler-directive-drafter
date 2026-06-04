from context_compiler_directive_drafter.drafter import draft_directive


def test_draft_directive_is_non_authoritative_placeholder() -> None:
    result = draft_directive("please make replies concise")

    assert result.user_input == "please make replies concise"
    assert result.candidate_directive is None
    assert result.confidence == 0.0
    assert result.authoritative is False
    assert result.rationale == "Drafting is not implemented yet."
