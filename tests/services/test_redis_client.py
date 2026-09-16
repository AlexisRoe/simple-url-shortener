"""Tests for app.services.redis_client."""

from unittest.mock import MagicMock

import redis

from app.core.config import Settings
from app.services.redis_client import build_redis_client, check_redis_connection


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
