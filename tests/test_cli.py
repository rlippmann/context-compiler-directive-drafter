"""Regression coverage for the current CLI surface."""

import json

from context_compiler_directive_drafter.cli import main


def test_cli_invocation_reports_host_engine_requirement(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["directive-drafter", "please make replies concise"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "public high-level drafting API requires a host-provided engine" in captured.err


def test_cli_help_exit_when_input_missing(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["directive-drafter"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "usage:" in captured.err


def test_cli_json_emits_status_payload_on_stdout(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["directive-drafter", "--json", "please make replies concise"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "available": False,
        "reason": "The public high-level drafting API requires a host-provided engine.",
    }
