"""Tests for backend.app.core.config."""

from __future__ import annotations

import pytest

from backend.app.core.config import Settings, get_settings


class TestSettings:
    """Tests for Settings model."""

    def test_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.com/v1")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4")
        monkeypatch.setenv("TUSHARE_TOKEN", "ts-test")

        settings = Settings()
        assert settings.openai_api_key == "test-key"
        assert settings.openai_base_url == "https://api.example.com/v1"
        assert settings.openai_model == "gpt-4"
        assert settings.tushare_token == "ts-test"

    def test_settings_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

        # Use a non-existent env_file to avoid .env overriding defaults
        from pydantic_settings import SettingsConfigDict

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=".env.nonexistent",
                env_file_encoding="utf-8",
                extra="ignore",
            )

        settings = TestSettings()
        assert settings.openai_base_url == "https://gw-stg.tradingbase.ai/v1"
        assert settings.openai_model == "gpt-4.1"
        assert settings.tushare_token is None
        assert settings.tool_top_k == 5

    def test_tool_top_k_bounds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("TOOL_TOP_K", "3")

        settings = Settings()
        assert settings.tool_top_k == 3

    def test_tool_top_k_too_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("TOOL_TOP_K", "0")

        with pytest.raises(Exception):
            Settings()

    def test_tool_top_k_too_high(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("TOOL_TOP_K", "10")

        with pytest.raises(Exception):
            Settings()

    def test_get_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = get_settings()
        assert isinstance(settings, Settings)
