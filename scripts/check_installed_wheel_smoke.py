"""Validate the installed wheel against checked-in public contracts."""

import json
import sys
from importlib.resources import files
from pathlib import Path

import context_compiler_directive_drafter as package


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_contract(relative_path: str) -> dict[str, object]:
    path = _repo_root() / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_installed_wheel_import() -> None:
    package_file = Path(package.__file__).resolve()
    repo_root = _repo_root()
    venv_root = Path(sys.prefix).resolve()

    assert not package_file.is_relative_to(repo_root), package_file
    assert package_file.is_relative_to(venv_root), package_file


def _assert_public_exports() -> None:
    contract = _load_contract("tests/fixtures/contracts/public-api-v1.json")
    exports = contract["exports"]["names"]
    forbidden_exports = contract.get("forbidden_exports", [])

    missing = sorted(name for name in exports if not hasattr(package, name))
    assert not missing, missing

    unexpected = sorted(name for name in forbidden_exports if hasattr(package, name))
    assert not unexpected, unexpected


def _assert_packaged_resources() -> None:
    assert (
        files("context_compiler_directive_drafter").joinpath("py.typed").read_text(encoding="utf-8")
        == ""
    )


def _assert_converter_prompt_behavior() -> None:
    contract = _load_contract("tests/fixtures/contracts/prompt-rendering-v1.json")
    probes = contract["members"]["get_converter_prompt"]["behavior_probes"]
    prompt = package.get_converter_prompt()

    for probe in probes:
        for substring in probe["expect_substrings"]:
            assert substring in prompt, substring
        for substring in probe.get("reject_substrings", []):
            assert substring not in prompt, substring


def main() -> None:
    _assert_installed_wheel_import()
    _assert_public_exports()
    _assert_packaged_resources()
    _assert_converter_prompt_behavior()
    print("wheel-smoke: ok")


if __name__ == "__main__":
    main()
