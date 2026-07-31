from pathlib import Path

from scripts import check_boundaries


def _write_scanned_file(tmp_path: Path, relative_path: str, content: str) -> Path:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _patterns_for(tmp_path: Path) -> set[str]:
    violations = check_boundaries.scan_roots(
        [
            tmp_path / "src" / "context_compiler_directive_drafter",
            tmp_path / "examples",
        ]
    )
    return {violation.check.pattern for violation in violations}


def test_scan_roots_ignores_tests_directory() -> None:
    tmp_path = Path("tmp_check_boundaries_ignore_tests")
    if tmp_path.exists():
        for path in sorted(tmp_path.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        tmp_path.rmdir()
    tmp_path.mkdir()
    try:
        _write_scanned_file(
            tmp_path,
            "tests/test_boundary_probe.py",
            "def probe(engine):\n    return engine.step('use docker')\n",
        )
        assert _patterns_for(tmp_path) == set()
    finally:
        for path in sorted(tmp_path.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        tmp_path.rmdir()


def test_boundary_checker_allows_read_only_engine_properties_and_type_imports(
    tmp_path: Path,
) -> None:
    _write_scanned_file(
        tmp_path,
        "src/context_compiler_directive_drafter/allowed.py",
        (
            "from context_compiler import Engine, create_engine\n\n"
            "def render_prompt(engine: Engine) -> tuple[str | None, object]:\n"
            "    fresh = create_engine()\n"
            "    return engine.premise, engine.policies or fresh\n"
        ),
    )

    assert _patterns_for(tmp_path) == set()


def test_boundary_checker_rejects_engine_step_in_package_source(tmp_path: Path) -> None:
    _write_scanned_file(
        tmp_path,
        "src/context_compiler_directive_drafter/bad.py",
        "def run(engine):\n    return engine.step('use docker')\n",
    )

    assert _patterns_for(tmp_path) == {"engine.step("}


def test_boundary_checker_rejects_engine_state_read_and_assignment(tmp_path: Path) -> None:
    _write_scanned_file(
        tmp_path,
        "src/context_compiler_directive_drafter/bad.py",
        "def run(engine):\n    current = engine.state\n    engine.state = current\n",
    )

    assert _patterns_for(tmp_path) == {"engine.state", ".state ="}


def test_boundary_checker_rejects_engine_internal_state_mutation(tmp_path: Path) -> None:
    _write_scanned_file(
        tmp_path,
        "examples/bad_example.py",
        "def run(engine):\n    engine._state['premise'] = 'concise'\n",
    )

    assert _patterns_for(tmp_path) == {"engine._state"}


def test_boundary_checker_rejects_forbidden_host_framework_imports(tmp_path: Path) -> None:
    _write_scanned_file(
        tmp_path,
        "examples/hostish.py",
        "from fastapi import FastAPI\napp = FastAPI()\n",
    )

    assert _patterns_for(tmp_path) == {"import fastapi"}
