from context_compiler_directive_drafter import get_converter_prompt


def test_get_converter_prompt_returns_non_empty_static_text() -> None:
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


def test_get_converter_prompt_includes_valid_and_non_directive_examples() -> None:
    prompt = get_converter_prompt()

    assert "User: please use docker" in prompt
    assert "Output: use docker" in prompt
    assert "User: can you help with lunch?" in prompt
    assert "User: I prefer concise replies." in prompt
    assert "Output: set premise concise replies" in prompt
    assert "User: set premise to concise replies" in prompt
