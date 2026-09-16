"""Redis/Valkey connection service.

Provides a single, cached Redis client built from application settings,
plus a lightweight health check used by the ``/status`` route.
"""

from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("redis")


def build_redis_client(settings: Settings) -> redis.Redis:
    """Construct a new Redis/Valkey client for the given settings.

    Args:
        settings: Application settings providing the Valkey host and port.

    Returns:
        A configured, lazily-connecting :class:`redis.Redis` client.
    """
    return redis.Redis(
        host=settings.valkey_host,
        port=settings.valkey_port,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )


@lru_cache
def get_redis_client() -> redis.Redis:
    """Return the process-wide cached Redis/Valkey client.

    Returns:
        The shared :class:`redis.Redis` client, built from the cached
        application settings.
    """
    return build_redis_client(get_settings())


def check_redis_connection(client: redis.Redis | None = None) -> bool:
    """Check whether the Redis/Valkey server is reachable.

    Args:
        client: The Redis client to check. Defaults to the shared, cached
            client from :func:`get_redis_client`.

    Returns:
        True if the server responded to a PING, False otherwise.
    """
    client = client or get_redis_client()
    try:
        return bool(client.ping())
    except redis.RedisError as exc:
        logger.warning("Redis connection check failed: %s", exc)
        return False
