from context_compiler_directive_drafter.cli import main


def test_cli_returns_placeholder_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["directive-drafter", "please make replies concise"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "drafting is not implemented yet" in captured.err
    assert "candidate_directive: none" in captured.err


def test_cli_help_exit_when_input_missing(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["directive-drafter"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "usage:" in captured.err
