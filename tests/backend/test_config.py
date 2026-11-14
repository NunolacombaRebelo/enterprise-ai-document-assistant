"""Tests for environment-based configuration (Agent 1-owned core).

Verifies that ``Settings`` loads with safe defaults (so the app starts on a clean machine with no
``.env`` and no credentials) and that environment variables override defaults. No network, no
credentials.
"""

from __future__ import annotations

import pytest

from enterprise_ai_document_assistant.core.config import Settings


def test_settings_defaults_start_without_credentials() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.api_port == 8000
    assert settings.frontend_port == 8501
    assert settings.api_base_url == "http://localhost:8000"
    # Phase 0 must start without an OpenAI API key.
    assert settings.openai_api_key is None


def test_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "9999")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-secret")

    settings = Settings(_env_file=None)

    assert settings.api_port == 9999
    assert settings.log_level == "DEBUG"
    assert settings.openai_api_key == "test-key-not-a-real-secret"


def test_settings_ignores_unknown_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    # extra="ignore" means unknown variables do not raise.
    monkeypatch.setenv("SOME_UNRELATED_VAR", "value")
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"


def test_settings_model_config_values() -> None:
    # Sanity check that the model is configured for env-based, case-insensitive settings that
    # ignore unknown variables (so stray env vars do not break startup).
    config = Settings.model_config
    assert config["extra"] == "ignore"
    assert config["case_sensitive"] is False
    assert config["env_file"] == ".env"
