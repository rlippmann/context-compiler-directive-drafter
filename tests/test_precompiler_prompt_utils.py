from pathlib import Path

from context_compiler_directive_drafter import render_prompt
from context_compiler_directive_drafter.constants import (
    PROMPT_TOKEN_NULL_OR_VALUE,
    PROMPT_TOKEN_POLICY_SET,
)


def _write_prompt(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def _empty_policies() -> dict[str, str]:
    return {}


def _populated_policies() -> dict[str, str]:
    return {"zeta": "use", "beta": "use", "alpha": "prohibit"}


def test_render_prompt_returns_none_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    assert render_prompt(missing, None, _empty_policies()) is None


def test_render_prompt_strips_leading_header_comments_and_blank_lines(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.txt"
    _write_prompt(
        prompt_file,
        "\n# header one\n  # header two\n\n"
        f"premise={PROMPT_TOKEN_NULL_OR_VALUE}\n"
        f"policies={PROMPT_TOKEN_POLICY_SET}\n",
    )

    rendered = render_prompt(prompt_file, None, _empty_policies())
    assert rendered is not None
    assert rendered.startswith("premise=null\n")
    assert "# header" not in rendered


def test_render_prompt_replaces_tokens_for_empty_state(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.txt"
    _write_prompt(
        prompt_file,
        f"premise={PROMPT_TOKEN_NULL_OR_VALUE}\npolicies={PROMPT_TOKEN_POLICY_SET}\n",
    )

    rendered = render_prompt(prompt_file, None, _empty_policies())
    assert rendered == "premise=null\npolicies=(none)"


def test_render_prompt_replaces_tokens_for_populated_inputs_with_sorted_policy_keys(
    tmp_path: Path,
) -> None:
    prompt_file = tmp_path / "prompt.txt"
    _write_prompt(
        prompt_file,
        f"premise={PROMPT_TOKEN_NULL_OR_VALUE}\npolicies={PROMPT_TOKEN_POLICY_SET}\n",
    )

    rendered = render_prompt(prompt_file, "concise replies", _populated_policies())
    assert rendered == "premise=concise replies\npolicies=alpha, beta, zeta"
