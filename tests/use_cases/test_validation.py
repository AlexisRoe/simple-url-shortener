"""Tests for the shared redirect-field validation helpers."""

import pytest

from app.core.config import get_settings
from app.core.errors import DomainNotAllowedError, InsecureUrlError, InvalidTtlError, InvalidUrlError
from app.use_cases.validation import validate_ttl, validate_url


def test_validate_url_accepts_https():
    validate_url("https://example.com")


def test_validate_url_rejects_http_with_insecure_url_error():
    with pytest.raises(InsecureUrlError):
        validate_url("http://example.com")


def test_validate_url_rejects_malformed_url_with_invalid_url_error():
    with pytest.raises(InvalidUrlError):
        validate_url("not-a-url")


def test_validate_url_rejects_domain_not_on_allowlist(monkeypatch):
    monkeypatch.setenv("ALLOWED_REDIRECT_DOMAINS", "company.com")
    get_settings.cache_clear()
    try:
        with pytest.raises(DomainNotAllowedError):
            validate_url("https://evil.com")
    finally:
        monkeypatch.delenv("ALLOWED_REDIRECT_DOMAINS", raising=False)
        get_settings.cache_clear()


def test_validate_url_accepts_domain_on_allowlist(monkeypatch):
    monkeypatch.setenv("ALLOWED_REDIRECT_DOMAINS", "company.com")
    get_settings.cache_clear()
    try:
        validate_url("https://docs.company.com")
    finally:
        monkeypatch.delenv("ALLOWED_REDIRECT_DOMAINS", raising=False)
        get_settings.cache_clear()


def test_validate_ttl_accepts_none_and_positive_int():
    validate_ttl(None)
    validate_ttl(500)


def test_validate_ttl_rejects_non_positive():
    with pytest.raises(InvalidTtlError):
        validate_ttl(0)
