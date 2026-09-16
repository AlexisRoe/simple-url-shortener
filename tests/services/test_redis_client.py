"""Tests for app.services.redis_client."""

from unittest.mock import MagicMock

import redis

from app.core.config import Settings
from app.services.redis_client import (
    build_redis_client,
    check_redis_connection,
    get_key_values_and_ttls,
    get_short_link_urls,
    scan_short_link_keys,
)


def test_build_redis_client_uses_settings_host_and_port():
    """The client is built using the host/port from the given settings."""
    settings = Settings(_env_file=None, VALKEY_HOST="example-host", VALKEY_PORT=1234)
    client = build_redis_client(settings)
    pool_kwargs = client.connection_pool.connection_kwargs
    assert pool_kwargs["host"] == "example-host"
    assert pool_kwargs["port"] == 1234


def test_check_redis_connection_true_on_successful_ping():
    """check_redis_connection returns True when the client's PING succeeds."""
    client = MagicMock()
    client.ping.return_value = True
    assert check_redis_connection(client) is True


def test_check_redis_connection_false_on_redis_error():
    """check_redis_connection returns False when the client raises a RedisError."""
    client = MagicMock()
    client.ping.side_effect = redis.RedisError("connection refused")
    assert check_redis_connection(client) is False


def test_get_short_link_urls_uses_get_when_no_variant():
    """Without a variant, only the base key is looked up via GET."""
    client = MagicMock()
    client.get.return_value = "https://example.com/base"

    variant_url, base_url = get_short_link_urls(client, "abc0000000", None)

    assert variant_url is None
    assert base_url == "https://example.com/base"
    client.get.assert_called_once_with("sh:abc0000000")


def test_get_short_link_urls_uses_mget_when_variant_given():
    """With a variant, both keys are looked up via MGET in one round trip."""
    client = MagicMock()
    client.mget.return_value = ["https://example.com/variant", "https://example.com/base"]

    variant_url, base_url = get_short_link_urls(client, "abc0000000", "ab")

    assert variant_url == "https://example.com/variant"
    assert base_url == "https://example.com/base"
    client.mget.assert_called_once_with("sh:abc0000000:ab", "sh:abc0000000")


def test_scan_short_link_keys_matches_prefix():
    """scan_short_link_keys queries with the sh:* prefix via SCAN."""
    client = MagicMock()
    client.scan_iter.return_value = iter(["sh:abc0000000", "sh:abc0000000:ab"])

    keys = scan_short_link_keys(client)

    assert keys == ["sh:abc0000000", "sh:abc0000000:ab"]
    client.scan_iter.assert_called_once_with(match="sh:*")


def test_get_key_values_and_ttls_returns_empty_for_no_keys():
    """No keys means no pipeline round trip is needed."""
    client = MagicMock()

    values, ttls = get_key_values_and_ttls(client, [])

    assert values == []
    assert ttls == []
    client.pipeline.assert_not_called()


def test_get_key_values_and_ttls_uses_one_pipeline_round_trip():
    """Values and TTLs for all keys are fetched via a single pipeline execute."""
    client = MagicMock()
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com/a", "https://example.com/b", 100, -1]
    client.pipeline.return_value = pipe

    values, ttls = get_key_values_and_ttls(client, ["sh:a", "sh:b"])

    assert values == ["https://example.com/a", "https://example.com/b"]
    assert ttls == [100, -1]
    client.pipeline.assert_called_once_with(transaction=False)
