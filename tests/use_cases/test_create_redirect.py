"""Tests for the create_redirect use-case."""

from unittest.mock import MagicMock

import pytest

from app.core.errors import InvalidTtlError, InvalidUrlError
from app.use_cases.create_redirect import create_redirect


def _fake_redis(code_exists=False, ttl=-1):
    client = MagicMock()
    client.exists.return_value = 1 if code_exists else 0
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com", ttl]
    client.pipeline.return_value = pipe
    return client


def test_create_redirect_stores_url_and_returns_entry():
    client = _fake_redis()

    result = create_redirect(redis_client=client, url="https://example.com", ttl=None)

    assert result.url == "https://example.com"
    assert result.ttl == -1
    assert result.variants == []
    client.set.assert_called_once()
    assert client.set.call_args.kwargs == {}
    args, kwargs = client.set.call_args
    assert args[1] == "https://example.com"
    assert "px" not in kwargs


def test_create_redirect_passes_ttl_as_px():
    client = _fake_redis(ttl=500)

    create_redirect(redis_client=client, url="https://example.com", ttl=500)

    _, kwargs = client.set.call_args
    assert kwargs["px"] == 500


def test_create_redirect_rejects_invalid_url():
    client = _fake_redis()
    with pytest.raises(InvalidUrlError):
        create_redirect(redis_client=client, url="not-a-url", ttl=None)


def test_create_redirect_rejects_non_positive_ttl():
    client = _fake_redis()
    with pytest.raises(InvalidTtlError):
        create_redirect(redis_client=client, url="https://example.com", ttl=0)
