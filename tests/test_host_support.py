import logging

import pytest

import host_support
from host_support.confirmation import (
    summarize_confirmation_update,
    summarize_confirmation_update_from_checkpoint,
    summarize_confirmation_update_from_engine,
)
from host_support.provider_mode import ProviderConfig, print_startup_config, resolve_provider_config


def test_host_support_public_exports() -> None:
    assert set(host_support.__all__) == {
        "ProviderConfig",
        "is_confirmation_text",
        "print_startup_config",
        "resolve_provider_config",
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" yes ", True),
        ("YES!!!", True),
        ("no, ", True),
        ("No thanks.", True),
        ("maybe", False),
    ],
)
def test_is_confirmation_text_normalizes_case_whitespace_and_punctuation(
    value: str, expected: bool
) -> None:
    assert host_support.is_confirmation_text(value) is expected


def test_summarize_confirmation_update_negative_returns_state_unchanged() -> None:
    assert summarize_confirmation_update("no.", {"replacement": {"kind": "use_only"}}) == (
        "State unchanged."
    )


def test_summarize_confirmation_update_use_only_returns_specific_summary() -> None:
    pending = {
        "replacement": {
            "kind": "use_only",
            "new_item": "  docker   compose ",
        }
    }
    assert summarize_confirmation_update("yes", pending) == "State updated: Use docker compose."


def test_summarize_confirmation_update_replace_use_returns_replaced_summary() -> None:
    pending = {
        "replacement": {
            "kind": "replace_use",
            "new_item": "podman",
            "old_item": "docker",
        }
    }
    assert summarize_confirmation_update("okay", pending) == (
        "State updated: Replaced docker with podman."
    )


def test_summarize_confirmation_update_prohibited_replace_prompt_has_specific_summary(
) -> None:
    pending = {
        "prompt_to_user": (
            '"docker" is currently prohibited. '
            'Did you mean to remove it and use "podman" instead?'
        ),
        "replacement": {
            "kind": "replace_use",
            "new_item": "podman",
            "old_item": "docker",
        },
    }
    assert summarize_confirmation_update("yes please", pending) == (
        "State updated: Removed prohibition on docker; use podman."
    )


def test_summarize_confirmation_update_malformed_pending_falls_back_to_generic_summary() -> None:
    assert summarize_confirmation_update("yes", {"replacement": "bad-shape"}) == "State updated."


def test_summarize_confirmation_update_use_only_empty_label_falls_back_to_generic_summary() -> None:
    pending = {
        "replacement": {
            "kind": "use_only",
            "new_item": "   ",
        }
    }
    assert summarize_confirmation_update("yes", pending) == "State updated."


def test_summarize_confirmation_update_replace_use_empty_label_falls_back_to_generic_summary(
) -> None:
    pending = {
        "replacement": {
            "kind": "replace_use",
            "new_item": "   ",
            "old_item": "docker",
        }
    }
    assert summarize_confirmation_update("yes", pending) == "State updated."


def test_summarize_confirmation_update_unknown_replacement_kind_falls_back_to_generic_summary(
) -> None:
    pending = {
        "replacement": {
            "kind": "unknown_kind",
        }
    }
    assert summarize_confirmation_update("yes", pending) == "State updated."


def test_summarize_confirmation_update_non_confirmation_text_falls_back_to_generic_summary(
) -> None:
    pending = {
        "replacement": {
            "kind": "use_only",
            "new_item": "docker",
        }
    }
    assert summarize_confirmation_update("maybe", pending) == "State updated."


def test_summarize_confirmation_update_from_checkpoint_reads_pending() -> None:
    checkpoint = {
        "pending": {
            "replacement": {
                "kind": "use_only",
                "new_item": "docker",
            }
        }
    }
    assert summarize_confirmation_update_from_checkpoint("yes", checkpoint) == (
        "State updated: Use docker."
    )


def test_summarize_confirmation_update_from_engine_handles_export_failure() -> None:
    class BrokenEngine:
        def export_checkpoint(self) -> object:
            raise RuntimeError("boom")

    assert summarize_confirmation_update_from_engine("yes", BrokenEngine()) == "State updated."


def test_resolve_provider_config_defaults_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.delenv("MODEL", raising=False)

    config = resolve_provider_config()

    assert config == ProviderConfig(
        mode="openai",
        source="default",
        base_url="https://api.openai.com/v1",
        model="openai/gpt-4o-mini",
        api_key="dummy",
    )


def test_resolve_provider_config_base_url_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("PROVIDER", "ollama")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MODEL", "demo-model")

    config = resolve_provider_config()

    assert config == ProviderConfig(
        mode="openai_compatible",
        source="OPENAI_BASE_URL override",
        base_url="https://example.test/v1",
        model="demo-model",
        api_key=None,
    )


def test_resolve_provider_config_rejects_invalid_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("PROVIDER", "bedrock")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    with pytest.raises(RuntimeError, match="Invalid PROVIDER value 'bedrock'"):
        resolve_provider_config()


def test_print_startup_config_logs_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    config = ProviderConfig(
        mode="ollama",
        source="PROVIDER",
        base_url="http://localhost:11434",
        model="demo-model",
        api_key=None,
    )

    monkeypatch.setattr("host_support.provider_mode._STARTUP_LOGGED", False)

    with caplog.at_level(logging.INFO):
        print_startup_config(config)
        print_startup_config(config)

    matches = [
        rec
        for rec in caplog.records
        if rec.getMessage().startswith("litellm_config mode=ollama")
    ]
    assert len(matches) == 1
