"""Application configuration: loading and validating environment variables.

All environment-derived configuration flows through :class:`Settings` and
:func:`get_settings`, so the rest of the codebase never reads ``os.environ``
directly. Invalid or missing configuration surfaces as a
:class:`~app.core.errors.ConfigurationError`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigurationError


class Settings(BaseSettings):
    """Typed, validated application settings sourced from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="simple-url-shortener", alias="APP_NAME")
    app_version: str = Field(default="0.0.0", alias="APP_VERSION")
    app_env: Literal["development", "production", "test"] = Field(default="development", alias="APP_ENV")

    valkey_host: str = Field(default="valkyr", alias="VALKEY_HOST")
    valkey_port: int = Field(default=6379, alias="VALKEY_PORT")

    api_token: str = Field(alias="API_TOKEN")

    default_redirect_url: str = Field(alias="DEFAULT_REDIRECT_URL")

    log_enabled: bool = Field(default=True, alias="LOG_ENABLED")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )
    log_style: Literal["text", "json"] = Field(default="text", alias="LOG_STYLE")

    @property
    def is_development(self) -> bool:
        """Whether the application is running in the development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Load and cache validated application settings.

    Cached with :func:`functools.lru_cache` so settings are parsed once per
    process; call ``get_settings.cache_clear()`` to force a reload (mainly
    useful in tests).

    Returns:
        The validated, process-wide :class:`Settings` instance.

    Raises:
        ConfigurationError: If required environment variables are missing
            or fail validation.
    """
    try:
        return Settings()
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid application configuration: {exc}") from exc
