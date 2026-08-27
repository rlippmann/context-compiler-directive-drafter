import runpy
from pathlib import Path


def _example_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "examples" / name


def test_basic_usage_example_runs(capsys) -> None:
    runpy.run_path(str(_example_path("basic_usage.py")), run_name="__main__")

    output = capsys.readouterr().out.strip().splitlines()
    assert output == ["candidate directive: use docker for container examples"]
