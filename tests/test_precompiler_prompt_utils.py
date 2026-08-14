from context_compiler.grammar import DirectiveKind, get_directive_metadata

from context_compiler_directive_drafter import get_converter_prompt
from context_compiler_directive_drafter import prompt_utils as prompt_module


def _expected_prompt_forms() -> list[str]:
    forms: list[str] = []
    for metadata in get_directive_metadata():
        if metadata.kind is DirectiveKind.REPLACE_USE:
            form = "`use <new item> instead of <old item>`"
        elif metadata.operand_names:
            operands = " ".join(f"<{name.replace('_', ' ')}>" for name in metadata.operand_names)
            form = f"`{metadata.canonical_start} {operands}`"
        else:
            form = f"`{metadata.canonical_start}`"
        forms.append(form)
    return forms


def _canonical_forms_section(prompt: str) -> str:
    start = prompt.index("Canonical directive forms:")
    end = prompt.index("What premise vs policy means:")
    return prompt[start:end]


def _behavior_examples_section(prompt: str) -> str:
    start = prompt.index("Examples of ordinary conversation that must not become directives:")
    return prompt[start:]


def _positive_acquisition_examples_section(prompt: str) -> str:
    start = prompt.index("Examples of interpretation-guided requests that may become directives:")
    end = prompt.index("Examples of ordinary conversation that must not become directives:")
    return prompt[start:end]


def test_get_converter_prompt_returns_non_empty_static_text() -> None:
    prompt_module._build_converter_prompt.cache_clear()
    prompt = get_converter_prompt()

    assert prompt
    assert prompt == prompt.strip()


def test_get_converter_prompt_does_not_include_state_injection_or_runtime_tokens() -> None:
    prompt = get_converter_prompt()

    assert "<NULL_OR_VALUE>" not in prompt
    assert "<SET OF CURRENT POLICY ITEMS>" not in prompt
    assert "Current compiler state:" not in prompt
    assert "engine.state" not in prompt


def test_get_converter_prompt_teaches_output_contract_and_scope() -> None:
    prompt = get_converter_prompt()

    assert "You are a directive converter that drafts candidate" in prompt
    assert "output exactly `<NO_DIRECTIVE>`" in prompt
    assert "Your output is a draft candidate only." in prompt
    assert "DirectiveDrafter" not in prompt


def test_get_converter_prompt_reflects_metadata_derived_canonical_inventory() -> None:
    prompt = get_converter_prompt()
    canonical_forms_section = _canonical_forms_section(prompt)

    assert "Canonical directive forms:" in prompt
    assert "Examples of canonical directive outputs:" not in prompt
    for form in _expected_prompt_forms():
        assert form in canonical_forms_section


def test_get_converter_prompt_keeps_grammar_inventory_out_of_behavior_examples() -> None:
    prompt = get_converter_prompt()
    behavior_examples = _behavior_examples_section(prompt)

    for inventory_example in (
        "`prohibit <item>`",
        "`remove policy <item>`",
        "`clear premise`",
        "`reset policies`",
        "`clear state`",
        "`use <new item> instead of <old item>`",
    ):
        assert inventory_example not in behavior_examples


def test_get_converter_prompt_includes_positive_acquisition_examples() -> None:
    prompt = get_converter_prompt()
    positive_examples = _positive_acquisition_examples_section(prompt)

    assert "User: please use docker" in positive_examples
    assert "User: switch from docker to podman" in positive_examples
    assert "User: make replies concise from now on" in positive_examples
    assert "User: change the standing premise to formal tone" in positive_examples
    assert "User: set premise to concise replies" in positive_examples
    assert "User: allow docker" in positive_examples
    assert "User: stop using peanuts" in positive_examples
    assert "User: I prefer concise replies." in positive_examples


def test_get_converter_prompt_positive_example_outputs_are_metadata_derived() -> None:
    prompt = get_converter_prompt()
    positive_examples = _positive_acquisition_examples_section(prompt)

    for expected_output in (
        "Output: use docker",
        "Output: use podman instead of docker",
        "Output: set premise concise replies",
        "Output: change premise to formal tone",
        "Output: prohibit peanuts",
    ):
        assert expected_output in positive_examples


def test_get_converter_prompt_preserves_behavioral_examples() -> None:
    prompt = get_converter_prompt()
    behavior_examples = _behavior_examples_section(prompt)
    positive_examples = _positive_acquisition_examples_section(prompt)

    assert "User: can you help with lunch?" in behavior_examples
    assert "User: use docker?" in behavior_examples
    assert 'User: He said "use docker".' in behavior_examples
    assert "User: set premise to concise replies" not in behavior_examples
    assert "User: allow docker" not in behavior_examples
    assert "User: stop using peanuts" not in behavior_examples
    assert "Output: set premise concise replies" in positive_examples


def test_get_converter_prompt_is_cached_after_first_generation(monkeypatch) -> None:
    prompt_module._build_converter_prompt.cache_clear()
    calls = 0
    original = prompt_module._render_canonical_forms

    def counting_render_canonical_forms() -> str:
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(prompt_module, "_render_canonical_forms", counting_render_canonical_forms)

    first = get_converter_prompt()
    second = get_converter_prompt()

    assert first == second
    assert first is second
    assert calls == 1
