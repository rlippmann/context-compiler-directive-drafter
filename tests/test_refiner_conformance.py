import json
from pathlib import Path

from context_compiler import create_engine
from context_compiler.grammar import decompose_directive

from context_compiler_directive_drafter import refine_directive

_REFINER_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "refiner"


def _fixture_paths() -> list[Path]:
    return sorted(_REFINER_FIXTURES_DIR.glob("*.json"))


def _load_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_exact_keys(payload: dict[str, object], expected: set[str], label: str) -> None:
    assert set(payload.keys()) == expected, label


def _assert_fixture_schema(path: Path, fixture: dict[str, object]) -> None:
    label = path.name
    _assert_exact_keys(fixture, {"name", "premise", "input", "expected"}, label)
    assert fixture["name"] == path.stem, label
    assert fixture["premise"] is None or isinstance(fixture["premise"], str), label
    assert isinstance(fixture["input"], str), label
    assert isinstance(fixture["expected"], str), label


def test_refiner_conformance_fixtures() -> None:
    for path in _fixture_paths():
        fixture = _load_fixture(path)
        _assert_fixture_schema(path, fixture)

        engine = create_engine(
            {
                "premise": fixture["premise"],
                "policies": {},
                "version": 2,
            }
        )
        before = engine.state

        directive = decompose_directive(fixture["input"])
        expected = decompose_directive(fixture["expected"])

        assert directive is not None, path.name
        assert expected is not None, path.name

        first = refine_directive(directive, engine)
        second = refine_directive(directive, engine)

        assert first == second, path.name
        assert first == expected, path.name
        assert engine.state == before, path.name
