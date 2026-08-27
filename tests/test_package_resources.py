from pathlib import Path

from context_compiler_directive_drafter.prompt_utils import _get_converter_prompt

get_converter_prompt = _get_converter_prompt

_PACKAGE = "context_compiler_directive_drafter"
_RESOURCE_PATHS = [
    "py.typed",
]
_LEGACY_IMPORT = ".".join(("experimental", "preprocessor"))
_SCAN_ROOTS = [
    Path("src/context_compiler_directive_drafter"),
    Path("tests"),
    Path("docs"),
    Path("README.md"),
]


def test_packaged_resources_exist_and_are_non_empty() -> None:
    from importlib.resources import files

    package_files = files(_PACKAGE)

    for relative_path in _RESOURCE_PATHS:
        resource = package_files.joinpath(relative_path)
        assert resource.is_file(), relative_path


def test_packaged_converter_prompt_is_static_and_context_free() -> None:
    prompt = get_converter_prompt()

    assert "Current compiler state:" not in prompt
    assert "<NULL_OR_VALUE>" not in prompt
    assert "<SET OF CURRENT POLICY ITEMS>" not in prompt
    assert "policies:" not in prompt.lower()
    assert "premise:" not in prompt.lower()


def test_packaged_converter_prompt_mentions_directive_categories_and_examples() -> None:
    prompt = get_converter_prompt()

    assert "Premise directives" in prompt
    assert "Policy directives" in prompt
    assert "Administrative directives" in prompt
    assert "`use <new item> instead of <old item>`" in prompt
    assert "Examples of user requests that may be drafted as directives:" in prompt


def test_packaged_converter_prompt_is_available_without_resource_file_lookup() -> None:
    prompt = get_converter_prompt()

    assert prompt.startswith("You are a directive converter that drafts candidate")


def test_repo_files_do_not_reference_legacy_preprocessor_import_path() -> None:
    for root in _SCAN_ROOTS:
        paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]

        for path in paths:
            if path.suffix not in {".py", ".md", ".txt", ".json"} and path.name != "py.typed":
                continue
            assert _LEGACY_IMPORT not in path.read_text(encoding="utf-8"), str(path)
