"""Tests for the update_redirect use-case."""

from unittest.mock import MagicMock

import pytest

from app.core.errors import InvalidTtlError, InvalidUrlError, InvalidVariantError, RedirectNotFoundError
from app.use_cases.update_redirect import update_redirect


def _fake_redis(key_exists=True, ttl=-1):
    client = MagicMock()
    client.exists.return_value = 1 if key_exists else 0
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com/new", ttl]
    client.pipeline.return_value = pipe
    return client


def test_update_redirect_updates_base_entry():
    client = _fake_redis()

    result = update_redirect(
        redis_client=client, code="aB3dE5gH7j", variant=None, url="https://example.com/new", ttl=None
    )

    assert result.code == "aB3dE5gH7j"
    assert result.variant is None
    assert result.url == "https://example.com/new"
    client.set.assert_called_once()
    client.zadd.assert_called_once()


def test_update_redirect_updates_variant_entry():
    client = _fake_redis()

    result = update_redirect(
        redis_client=client, code="aB3dE5gH7j", variant="ab", url="https://example.com/new", ttl=None
    )

    assert result.variant == "ab"
    client.zadd.assert_not_called()


def test_update_redirect_raises_when_entry_missing():
    client = _fake_redis(key_exists=False)
    with pytest.raises(RedirectNotFoundError):
        update_redirect(
            redis_client=client, code="aB3dE5gH7j", variant=None, url="https://example.com/new", ttl=None
        )


def test_update_redirect_rejects_invalid_variant_format():
    client = _fake_redis()
    with pytest.raises(InvalidVariantError):
        update_redirect(
            redis_client=client, code="aB3dE5gH7j", variant="123", url="https://example.com/new", ttl=None
        )


def test_update_redirect_rejects_invalid_url():
    client = _fake_redis()
    with pytest.raises(InvalidUrlError):
        update_redirect(redis_client=client, code="aB3dE5gH7j", variant=None, url="not-a-url", ttl=None)


def test_update_redirect_rejects_non_positive_ttl():
    client = _fake_redis()
    with pytest.raises(InvalidTtlError):
        update_redirect(
            redis_client=client, code="aB3dE5gH7j", variant=None, url="https://example.com/new", ttl=0
        )
