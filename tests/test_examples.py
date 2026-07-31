import runpy
from pathlib import Path


def _example_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "examples" / name


def test_basic_usage_example_runs(capsys) -> None:
    runpy.run_path(str(_example_path("basic_usage.py")), run_name="__main__")

    output = capsys.readouterr().out.strip().splitlines()
    assert output == [
        (
            "heuristic result: {'outcome': 'directive', 'directive': 'use docker', "
            "'rule_id': 'canonical.full_match'}"
        ),
        "validated candidate: use docker",
        (
            "ambiguous result: {'outcome': 'unknown', 'directive': None, "
            "'rule_id': 'reject.question_form'}"
        ),
        "ambiguous candidate: None",
    ]


def test_prompt_rendering_example_runs(capsys) -> None:
    runpy.run_path(str(_example_path("prompt_rendering.py")), run_name="__main__")

    output = capsys.readouterr().out
    assert output.strip()
    assert "* premise: concise replies" in output
    assert "* policies: docker, peanuts" in output
    assert "<NULL_OR_VALUE>" not in output
    assert "<SET OF CURRENT POLICY ITEMS>" not in output
