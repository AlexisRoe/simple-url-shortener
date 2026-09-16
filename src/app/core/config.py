"""Application configuration: loading and validating environment variables.

All environment-derived configuration flows through :class:`Settings` and
:func:`get_settings`, so the rest of the codebase never reads ``os.environ``
directly. Invalid or missing configuration surfaces as a
:class:`~app.core.errors.ConfigurationError`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.errors import ConfigurationError


class Settings(BaseSettings):
    """Typed, validated application settings sourced from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="simple-url-shortener", alias="APP_NAME")
    app_version: str = Field(default="0.0.0", alias="APP_VERSION")
    app_env: Literal["development", "production", "test"] = Field(default="development", alias="APP_ENV")

    valkey_host: str = Field(default="valkyr", alias="VALKEY_HOST")
    valkey_port: int = Field(default=6379, alias="VALKEY_PORT")

    # Three scoped bearer tokens forming a hierarchy (read < read_write <
    # delete): a higher-scoped token is also accepted wherever a lower
    # scope is required. Each carries its own expiry so a stale token
    # fails loudly (401) rather than remaining valid forever.
    api_token_read: str = Field(alias="API_TOKEN_READ")
    api_token_read_expires_at: datetime = Field(alias="API_TOKEN_READ_EXPIRES_AT")

    api_token_read_write: str = Field(alias="API_TOKEN_READ_WRITE")
    api_token_read_write_expires_at: datetime = Field(alias="API_TOKEN_READ_WRITE_EXPIRES_AT")

    api_token_delete: str = Field(alias="API_TOKEN_DELETE")
    api_token_delete_expires_at: datetime = Field(alias="API_TOKEN_DELETE_EXPIRES_AT")

    default_redirect_url: str = Field(alias="DEFAULT_REDIRECT_URL")

    # Comma-separated list of domains redirects are allowed to target
    # (e.g. "docs.company.com,tools.company.com"). An empty list disables
    # the restriction, allowing redirects to any https URL.
    allowed_redirect_domains: Annotated[list[str], NoDecode] = Field(
        default_factory=list, alias="ALLOWED_REDIRECT_DOMAINS"
    )

    log_enabled: bool = Field(default=True, alias="LOG_ENABLED")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )
    log_style: Literal["text", "json"] = Field(default="text", alias="LOG_STYLE")

    @field_validator("allowed_redirect_domains", mode="before")
    @classmethod
    def _split_allowed_redirect_domains(cls, value: object) -> object:
        """Parse the comma-separated ``ALLOWED_REDIRECT_DOMAINS`` env var into a list.

        Args:
            value: The raw env value (a comma-separated string), or an
                already-parsed list (e.g. when constructing ``Settings``
                directly in tests).

        Returns:
            A list of lowercased, whitespace-trimmed domains, empty
            entries dropped.
        """
        if isinstance(value, str):
            return [domain.strip().lower() for domain in value.split(",") if domain.strip()]

        return value

    @field_validator(
        "api_token_read_expires_at", "api_token_read_write_expires_at", "api_token_delete_expires_at"
    )
    @classmethod
    def _assume_utc_if_naive(cls, value: datetime) -> datetime:
        """Treat a timezone-naive expiry (e.g. "2026-12-31") as UTC.

        Args:
            value: The parsed expiry datetime.

        Returns:
            ``value`` unchanged if already timezone-aware, otherwise
            ``value`` with UTC attached.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value

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
