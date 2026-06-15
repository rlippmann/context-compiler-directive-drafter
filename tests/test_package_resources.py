from importlib.resources import as_file, files
from pathlib import Path

from context_compiler import create_engine

from context_compiler_directive_drafter import render_prompt

_PACKAGE = "context_compiler_directive_drafter"
_RESOURCE_PATHS = [
    "prompts/default.txt",
    "prompts/llama.txt",
    "py.typed",
]
_NON_EMPTY_RESOURCE_PATHS = [
    "prompts/default.txt",
    "prompts/llama.txt",
]
_LEGACY_IMPORT = ".".join(("experimental", "preprocessor"))
_SCAN_ROOTS = [
    Path("src/context_compiler_directive_drafter"),
    Path("tests"),
    Path("docs"),
    Path("README.md"),
]


def _empty_state():
    return create_engine().state


def _state_with_duplicate_policy_name() -> object:
    engine = create_engine()
    engine.step("use shared")
    engine.step("prohibit shared")
    return engine.state


def _state_with_punctuation_and_newline_premise() -> object:
    engine = create_engine()
    engine.step("set premise first line\nsecond line!")
    return engine.state


def _state_with_multiple_policy_names() -> object:
    engine = create_engine()
    engine.step("use zeta")
    engine.step("use beta")
    engine.step("prohibit alpha")
    return engine.state


def test_packaged_resources_exist_and_are_non_empty() -> None:
    package_files = files(_PACKAGE)

    for relative_path in _RESOURCE_PATHS:
        resource = package_files.joinpath(relative_path)
        assert resource.is_file(), relative_path

    for relative_path in _NON_EMPTY_RESOURCE_PATHS:
        resource = package_files.joinpath(relative_path)
        assert resource.read_text(encoding="utf-8").strip(), relative_path


def test_packaged_default_prompt_renders_from_installed_resource_text() -> None:
    prompt_resource = files(_PACKAGE).joinpath("prompts/default.txt")

    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, _empty_state())

    assert rendered is not None
    assert rendered.strip()
    assert "<NULL_OR_VALUE>" not in rendered
    assert "<SET OF CURRENT POLICY ITEMS>" not in rendered


def test_packaged_llama_prompt_renders_from_installed_resource_text() -> None:
    prompt_resource = files(_PACKAGE).joinpath("prompts/llama.txt")

    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, _empty_state())

    assert rendered is not None
    assert rendered.strip()
    assert "<NULL_OR_VALUE>" not in rendered
    assert "<SET OF CURRENT POLICY ITEMS>" not in rendered


def test_packaged_default_prompt_duplicate_policy_names_render_once() -> None:
    prompt_resource = files(_PACKAGE).joinpath("prompts/default.txt")

    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, _state_with_duplicate_policy_name())

    assert rendered is not None
    assert "* policies: shared" in rendered
    assert rendered.count("shared") == 1


def test_packaged_llama_prompt_duplicate_policy_names_render_once() -> None:
    prompt_resource = files(_PACKAGE).joinpath("prompts/llama.txt")

    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, _state_with_duplicate_policy_name())

    assert rendered is not None
    assert "* policies: shared" in rendered
    assert rendered.count("shared") == 1


def test_packaged_default_prompt_renders_sorted_multiple_policy_names() -> None:
    prompt_resource = files(_PACKAGE).joinpath("prompts/default.txt")

    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, _state_with_multiple_policy_names())

    assert rendered is not None
    assert "* policies: alpha, beta, zeta" in rendered


def test_packaged_llama_prompt_renders_sorted_multiple_policy_names() -> None:
    prompt_resource = files(_PACKAGE).joinpath("prompts/llama.txt")

    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, _state_with_multiple_policy_names())

    assert rendered is not None
    assert "* policies: alpha, beta, zeta" in rendered


def test_packaged_default_prompt_renders_punctuation_and_newline_premise_deterministically() -> (
    None
):
    prompt_resource = files(_PACKAGE).joinpath("prompts/default.txt")

    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, _state_with_punctuation_and_newline_premise())

    assert rendered is not None
    assert "* premise: first line second line!" in rendered


def test_packaged_llama_prompt_renders_punctuation_and_newline_premise_deterministically() -> None:
    prompt_resource = files(_PACKAGE).joinpath("prompts/llama.txt")

    with as_file(prompt_resource) as prompt_path:
        rendered = render_prompt(prompt_path, _state_with_punctuation_and_newline_premise())

    assert rendered is not None
    assert "* premise: first line second line!" in rendered


def test_repo_files_do_not_reference_legacy_preprocessor_import_path() -> None:
    for root in _SCAN_ROOTS:
        paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]

        for path in paths:
            if path.suffix not in {".py", ".md", ".txt", ".json"} and path.name != "py.typed":
                continue
            assert _LEGACY_IMPORT not in path.read_text(encoding="utf-8"), str(path)
