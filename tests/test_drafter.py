"""Placeholder-only regression coverage for the current drafter entrypoint."""

from context_compiler_directive_drafter.drafter import draft_directive


def test_draft_directive_placeholder_remains_non_authoritative_stub() -> None:
    result = draft_directive("please make replies concise")

    assert result.user_input == "please make replies concise"
    assert result.candidate_directive is None
    assert result.confidence == 0.0
    assert result.authoritative is False
    assert result.rationale == "Drafting is not implemented yet."
