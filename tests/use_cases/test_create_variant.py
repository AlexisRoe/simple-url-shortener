"""Tests for the create_variant use-case."""

from unittest.mock import MagicMock

import pytest

from app.core.errors import InvalidTtlError, InvalidUrlError, InvalidVariantError, RedirectNotFoundError
from app.use_cases.create_variant import create_variant


def _fake_redis(code_exists=True, ttl=200):
    client = MagicMock()
    client.exists.return_value = 1 if code_exists else 0
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com/v", ttl]
    client.pipeline.return_value = pipe
    return client


def test_create_variant_stores_and_returns_entry():
    client = _fake_redis()

    result = create_variant(
        redis_client=client, code="aB3dE5gH7j", variant="ab", url="https://example.com/v", ttl=None
    )

    assert result.code == "aB3dE5gH7j"
    assert result.variant == "ab"
    assert result.url == "https://example.com/v"
    assert result.ttl == 200
    client.set.assert_called_once()


def test_create_variant_raises_when_code_missing():
    client = _fake_redis(code_exists=False)
    with pytest.raises(RedirectNotFoundError):
        create_variant(
            redis_client=client, code="aB3dE5gH7j", variant="ab", url="https://example.com/v", ttl=None
        )


def test_create_variant_rejects_invalid_variant_format():
    client = _fake_redis()
    with pytest.raises(InvalidVariantError):
        create_variant(
            redis_client=client, code="aB3dE5gH7j", variant="123", url="https://example.com/v", ttl=None
        )


def test_create_variant_rejects_invalid_url():
    client = _fake_redis()
    with pytest.raises(InvalidUrlError):
        create_variant(redis_client=client, code="aB3dE5gH7j", variant="ab", url="not-a-url", ttl=None)


def test_create_variant_rejects_non_positive_ttl():
    client = _fake_redis()
    with pytest.raises(InvalidTtlError):
        create_variant(
            redis_client=client, code="aB3dE5gH7j", variant="ab", url="https://example.com/v", ttl=-5
        )
