import runpy
from pathlib import Path


def _example_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "examples" / name


def test_basic_usage_example_runs(capsys) -> None:
    runpy.run_path(str(_example_path("basic_usage.py")), run_name="__main__")

    output = capsys.readouterr().out
    assert "validated candidate: use docker" in output
    assert "ambiguous candidate: None" in output


def test_prompt_rendering_example_runs(capsys) -> None:
    runpy.run_path(str(_example_path("prompt_rendering.py")), run_name="__main__")

    output = capsys.readouterr().out
    assert "* premise: concise replies" in output
    assert "* policies: docker, peanuts" in output
