"""Tests for app.core.security."""

from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.security import Role, extract_bearer_token, required_role_for_method, resolve_token


def test_extract_bearer_token_returns_token():
    """A well-formed Bearer header yields the token."""
    assert extract_bearer_token("Bearer abc123") == "abc123"


def test_extract_bearer_token_is_case_insensitive_on_scheme():
    """The "Bearer" scheme is matched case-insensitively."""
    assert extract_bearer_token("bearer abc123") == "abc123"


def test_extract_bearer_token_returns_none_when_missing():
    """A missing header returns None."""
    assert extract_bearer_token(None) is None


def test_extract_bearer_token_returns_none_for_wrong_scheme():
    """A non-Bearer scheme (e.g. Basic) returns None."""
    assert extract_bearer_token("Basic abc123") is None


def test_extract_bearer_token_returns_none_for_malformed_header():
    """A header with no token portion returns None."""
    assert extract_bearer_token("Bearer") is None


def test_required_role_for_method():
    assert required_role_for_method("GET") is Role.READ
    assert required_role_for_method("POST") is Role.READ_WRITE
    assert required_role_for_method("PATCH") is Role.READ_WRITE
    assert required_role_for_method("DELETE") is Role.DELETE


def _settings(**overrides: str) -> Settings:
    future = "2099-01-01T00:00:00Z"
    defaults = {
        "API_TOKEN_READ": "read-token",
        "API_TOKEN_READ_EXPIRES_AT": future,
        "API_TOKEN_READ_WRITE": "read-write-token",
        "API_TOKEN_READ_WRITE_EXPIRES_AT": future,
        "API_TOKEN_DELETE": "delete-token",
        "API_TOKEN_DELETE_EXPIRES_AT": future,
        "DEFAULT_REDIRECT_URL": "https://example.com",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_resolve_token_returns_none_for_missing_token():
    assert resolve_token(None, _settings()) is None


def test_resolve_token_returns_none_for_unrecognized_token():
    assert resolve_token("nope", _settings()) is None


def test_resolve_token_matches_each_configured_role():
    settings = _settings()

    assert resolve_token("read-token", settings).role is Role.READ
    assert resolve_token("read-write-token", settings).role is Role.READ_WRITE
    assert resolve_token("delete-token", settings).role is Role.DELETE


def test_resolve_token_reports_expired():
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    settings = _settings(API_TOKEN_READ_EXPIRES_AT=past)

    matched = resolve_token("read-token", settings)

    assert matched is not None
    assert matched.is_expired is True


def test_resolve_token_reports_not_expired():
    matched = resolve_token("read-token", _settings())

    assert matched is not None
    assert matched.is_expired is False


def test_role_hierarchy_ordering():
    assert Role.READ < Role.READ_WRITE < Role.DELETE
