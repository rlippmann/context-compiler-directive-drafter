import runpy
from pathlib import Path


def _example_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "examples" / name


def test_basic_usage_example_runs(capsys) -> None:
    runpy.run_path(str(_example_path("basic_usage.py")), run_name="__main__")

    output = capsys.readouterr().out.strip().splitlines()
    assert output == [
        "heuristic result: {'outcome': 'directive', 'directive': 'use docker'}",
        "validated candidate: use docker",
        (
            "ambiguous result: {'outcome': 'unknown', 'directive': None, "
            "'reason': 'reject.question_form'}"
        ),
        "ambiguous candidate: None",
        "fallback candidate: use podman",
    ]


def test_prompt_rendering_example_runs(capsys) -> None:
    runpy.run_path(str(_example_path("prompt_rendering.py")), run_name="__main__")

    output = capsys.readouterr().out
    assert output.strip()
    assert "You are a directive converter that drafts candidate" in output
    assert "Directive categories:" in output
    assert "Canonical directive forms:" in output
