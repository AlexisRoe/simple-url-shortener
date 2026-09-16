"""Redis/Valkey connection service.

Provides a single, cached Redis client built from application settings,
plus a lightweight health check used by the ``/status`` route.
"""

from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import Settings, get_settings
from app.core.constants import SHORT_CODE_KEY_PREFIX
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


def get_short_link_urls(client: redis.Redis, code: str, variant: str | None) -> tuple[str | None, str | None]:
    """Look up the stored redirect targets for a short code and variant.

    Args:
        client: The Redis/Valkey client to query.
        code: The short code, already validated by the caller.
        variant: The optional variant string, or None if not supplied.

    Returns:
        A ``(variant_url, base_url)`` tuple. ``variant_url`` is always
        None when ``variant`` is None.
    """
    base_key = f"{SHORT_CODE_KEY_PREFIX}:{code}"

    if variant is None:
        return None, client.get(base_key)

    variant_key = f"{base_key}:{variant}"
    variant_url, base_url = client.mget(variant_key, base_key)

    return variant_url, base_url


def scan_short_link_keys(client: redis.Redis) -> list[str]:
    """Return all short-link keys (base and variant) via a non-blocking SCAN.

    Args:
        client: The Redis/Valkey client to query.

    Returns:
        Every key matching ``<SHORT_CODE_KEY_PREFIX>:*``, in no particular
        order.
    """
    return list(client.scan_iter(match=f"{SHORT_CODE_KEY_PREFIX}:*"))


def get_key_values_and_ttls(client: redis.Redis, keys: list[str]) -> tuple[list[str | None], list[int]]:
    """Fetch the value and TTL of each given key in a single round trip.

    Args:
        client: The Redis/Valkey client to query.
        keys: The keys to fetch.

    Returns:
        A ``(values, ttls)`` tuple, each parallel to ``keys``. A TTL of
        ``-1`` means the key has no expiry set; ``-2`` means the key
        doesn't exist (e.g. it expired between the scan and this call).
    """
    if not keys:
        return [], []

    pipe = client.pipeline(transaction=False)
    for key in keys:
        pipe.get(key)
    for key in keys:
        pipe.ttl(key)

    results = pipe.execute()
    midpoint = len(keys)
    return results[:midpoint], results[midpoint:]


def build_short_link_key(code: str, variant: str | None = None) -> str:
    """Build the Redis key for a code, or a code+variant.

    Args:
        code: The short code.
        variant: The optional variant string.

    Returns:
        ``sh:<code>`` or ``sh:<code>:<variant>``.
    """
    key = f"{SHORT_CODE_KEY_PREFIX}:{code}"

    return f"{key}:{variant}" if variant else key


def key_exists(client: redis.Redis, key: str) -> bool:
    """Check whether a key currently exists.

    Args:
        client: The Redis/Valkey client to query.
        key: The key to check.

    Returns:
        True if the key exists.
    """
    return bool(client.exists(key))


def set_short_link(client: redis.Redis, key: str, url: str, ttl_ms: int | None) -> None:
    """Store a redirect target URL, optionally with an expiry.

    Args:
        client: The Redis/Valkey client to write to.
        key: The key to write (base or variant).
        url: The redirect target URL to store.
        ttl_ms: The expiry in milliseconds, or None to store forever.
    """
    if ttl_ms is None:
        client.set(key, url)
    else:
        client.set(key, url, px=ttl_ms)


def delete_key(client: redis.Redis, key: str) -> bool:
    """Delete a single key.

    Args:
        client: The Redis/Valkey client to write to.
        key: The key to delete.

    Returns:
        True if a key was deleted, False if it didn't exist.
    """
    return bool(client.delete(key))


def delete_keys(client: redis.Redis, keys: list[str]) -> int:
    """Delete multiple keys in a single round trip.

    Args:
        client: The Redis/Valkey client to write to.
        keys: The keys to delete.

    Returns:
        The number of keys actually deleted.
    """
    if not keys:
        return 0

    return client.delete(*keys)


def scan_keys_for_code(client: redis.Redis, code: str) -> list[str]:
    """Return the base key and any variant keys belonging to one code.

    Args:
        client: The Redis/Valkey client to query.
        code: The short code whose keys to scan for.

    Returns:
        Every key matching ``<SHORT_CODE_KEY_PREFIX>:<code>`` or
        ``<SHORT_CODE_KEY_PREFIX>:<code>:*``.
    """
    return list(client.scan_iter(match=f"{SHORT_CODE_KEY_PREFIX}:{code}*"))
