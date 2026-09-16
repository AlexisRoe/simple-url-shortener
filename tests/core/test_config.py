"""Tests for app.core.config."""

import pytest

from app.core.config import Settings, get_settings
from app.core.errors import ConfigurationError


def test_settings_defaults():
    """Settings fall back to their documented defaults when unset."""
    settings = Settings(_env_file=None)
    assert settings.app_name == "simple-url-shortener"
    assert settings.app_env == "development"
    assert settings.valkey_host == "valkyr"
    assert settings.valkey_port == 6379
    assert settings.valkey_username == "test-valkey-user"
    assert settings.valkey_password == "test-valkey-password"
    assert settings.log_enabled is True
    assert settings.log_level == "INFO"
    assert settings.log_style == "text"


def test_settings_reads_env_overrides(monkeypatch):
    """Settings are overridden by matching environment variables."""
    monkeypatch.setenv("APP_NAME", "custom-name")
    monkeypatch.setenv("VALKEY_PORT", "1234")
    settings = Settings(_env_file=None)
    assert settings.app_name == "custom-name"
    assert settings.valkey_port == 1234


def test_is_development_property():
    """is_development reflects the app_env field."""
    assert Settings(_env_file=None, APP_ENV="development").is_development is True
    assert Settings(_env_file=None, APP_ENV="production").is_development is False


def test_get_settings_wraps_validation_error(monkeypatch):
    """get_settings raises ConfigurationError when validation fails."""
    monkeypatch.setenv("APP_ENV", "not-a-real-environment")
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigurationError):
            get_settings()
    finally:
        monkeypatch.delenv("APP_ENV", raising=False)
        get_settings.cache_clear()


def test_get_settings_is_cached(monkeypatch):
    """get_settings returns the same instance across calls until cleared."""
    get_settings.cache_clear()
    try:
        first = get_settings()
        second = get_settings()
        assert first is second
    finally:
        get_settings.cache_clear()
