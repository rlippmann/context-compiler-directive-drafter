"""Regression coverage for the current CLI surface."""

import json

from context_compiler_directive_drafter.cli import main


def test_cli_placeholder_invocation_returns_placeholder_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["directive-drafter", "please make replies concise"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Drafting orchestration requires an engine for refinement" in captured.err
    assert "candidate_directive: none" in captured.err


def test_cli_help_exit_when_input_missing(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["directive-drafter"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "usage:" in captured.err


def test_cli_json_emits_placeholder_payload_on_stdout(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["directive-drafter", "--json", "please make replies concise"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "authoritative": False,
        "candidate_directive": None,
        "outcome": "unknown",
        "refined_directive": None,
        "rationale": "Drafting orchestration requires an engine for refinement.",
        "rule_id": None,
        "user_input": "please make replies concise",
    }
