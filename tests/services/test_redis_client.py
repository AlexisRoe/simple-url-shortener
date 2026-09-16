"""Tests for app.services.redis_client."""

from unittest.mock import MagicMock

import redis

from app.core.config import Settings
from app.services.redis_client import build_redis_client, check_redis_connection, get_short_link_urls


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
