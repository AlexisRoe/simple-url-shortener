"""Tests for app.use_cases.resolve_short_link."""

from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.errors import InvalidShortCodeError, InvalidVariantError
from app.use_cases.resolve_short_link import resolve_short_link

VALID_CODE = "aB3dE5gH7j"


@pytest.fixture
def settings():
    return Settings(_env_file=None, DEFAULT_REDIRECT_URL="https://example.com/default")


@pytest.fixture
def redis_client():
    return MagicMock()


def test_rejects_invalid_code_format(redis_client, settings):
    with pytest.raises(InvalidShortCodeError):
        resolve_short_link("not valid!", None, redis_client=redis_client, settings=settings)


def test_rejects_invalid_variant_format(redis_client, settings):
    with pytest.raises(InvalidVariantError):
        resolve_short_link(VALID_CODE, "has spaces", redis_client=redis_client, settings=settings)


def test_rejects_variant_too_long(redis_client, settings):
    with pytest.raises(InvalidVariantError):
        resolve_short_link(VALID_CODE, "a" * 11, redis_client=redis_client, settings=settings)


def test_returns_base_url_when_no_variant(redis_client, settings):
    redis_client.get.return_value = "https://example.com/base"

    result = resolve_short_link(VALID_CODE, None, redis_client=redis_client, settings=settings)

    assert result == "https://example.com/base"
    redis_client.get.assert_called_once_with(f"sh:{VALID_CODE}")


def test_returns_variant_url_when_present(redis_client, settings):
    redis_client.mget.return_value = ["https://example.com/variant", "https://example.com/base"]

    result = resolve_short_link(VALID_CODE, "ab", redis_client=redis_client, settings=settings)

    assert result == "https://example.com/variant"
    redis_client.mget.assert_called_once_with(f"sh:{VALID_CODE}:ab", f"sh:{VALID_CODE}")


def test_falls_back_to_base_url_when_variant_missing(redis_client, settings):
    redis_client.mget.return_value = [None, "https://example.com/base"]

    result = resolve_short_link(VALID_CODE, "ab", redis_client=redis_client, settings=settings)

    assert result == "https://example.com/base"


def test_falls_back_to_default_url_when_nothing_found(redis_client, settings):
    redis_client.get.return_value = None

    result = resolve_short_link(VALID_CODE, None, redis_client=redis_client, settings=settings)

    assert result == settings.default_redirect_url


def test_falls_back_to_default_url_when_variant_and_base_missing(redis_client, settings):
    redis_client.mget.return_value = [None, None]

    result = resolve_short_link(VALID_CODE, "ab", redis_client=redis_client, settings=settings)

    assert result == settings.default_redirect_url
