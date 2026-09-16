"""Tests for the get_redirect use-case."""

from unittest.mock import MagicMock

import pytest

from app.core.errors import RedirectNotFoundError
from app.use_cases.get_redirect import get_redirect


def _fake_redis(keys, values, ttls):
    client = MagicMock()
    client.scan_iter.return_value = iter(keys)
    pipe = MagicMock()
    pipe.execute.return_value = [*values, *ttls]
    client.pipeline.return_value = pipe
    return client


def test_get_redirect_returns_entry_with_variants():
    keys = ["sh:aB3dE5gH7j", "sh:aB3dE5gH7j:ab"]
    values = ["https://example.com", "https://example.com/v"]
    ttls = [100, 200]
    client = _fake_redis(keys, values, ttls)

    result = get_redirect(redis_client=client, code="aB3dE5gH7j")

    assert result.code == "aB3dE5gH7j"
    assert result.url == "https://example.com"
    assert result.ttl == 100
    assert len(result.variants) == 1
    assert result.variants[0].variant == "ab"


def test_get_redirect_raises_when_missing():
    client = _fake_redis([], [], [])
    with pytest.raises(RedirectNotFoundError):
        get_redirect(redis_client=client, code="aB3dE5gH7j")
