"""Redis/Valkey connection service.

Provides a single, cached Redis client built from application settings,
plus a lightweight health check used by the ``/status`` route.
"""

from __future__ import annotations

import time
from functools import lru_cache

import redis

from app.core.config import Settings, get_settings
from app.core.constants import SHORT_CODE_INDEX_KEY, SHORT_CODE_KEY_PREFIX
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
        username=settings.valkey_username,
        password=settings.valkey_password,
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


def add_code_to_index(client: redis.Redis, code: str, ttl_ms: int | None) -> None:
    """Add (or refresh) a base short code's entry in the listing index.

    Only base codes are indexed, never variants -- variants are picked up
    per-code via :func:`scan_keys_for_code` when a page is fetched.

    Args:
        client: The Redis/Valkey client to write to.
        code: The base short code to index.
        ttl_ms: The code's expiry in milliseconds, or None if it never
            expires. Stored as the ZSET score (now + ttl_ms), so expired
            codes naturally sort below ``now`` and can be range-excluded
            or purged. Codes with no TTL are scored ``+inf``.
    """
    score = float("inf") if ttl_ms is None else time.time() * 1000 + ttl_ms
    client.zadd(SHORT_CODE_INDEX_KEY, {code: score})


def remove_code_from_index(client: redis.Redis, code: str) -> None:
    """Remove a base short code's entry from the listing index.

    Args:
        client: The Redis/Valkey client to write to.
        code: The base short code to remove from the index.
    """
    client.zrem(SHORT_CODE_INDEX_KEY, code)


def purge_expired_index_entries(client: redis.Redis, now_ms: float) -> int:
    """Remove index entries whose score (expiry timestamp) has passed.

    Called inline before reading the index so the index stays accurate
    without a dedicated background task. Cheap and idempotent, so it's
    safe to call on every read even if run from multiple processes.

    Args:
        client: The Redis/Valkey client to write to.
        now_ms: The current time in milliseconds since epoch.

    Returns:
        The number of stale entries removed.
    """
    return client.zremrangebyscore(SHORT_CODE_INDEX_KEY, "-inf", now_ms)


def get_index_count(client: redis.Redis, now_ms: float) -> int:
    """Count non-expired codes currently in the listing index.

    Args:
        client: The Redis/Valkey client to query.
        now_ms: The current time in milliseconds since epoch.

    Returns:
        The number of indexed codes with a score >= now_ms.
    """
    return client.zcount(SHORT_CODE_INDEX_KEY, now_ms, "+inf")


# NOTE: purge_expired_index_entries() above is called inline (once per
# listing request) rather than from a background task. That's sufficient at
# this app's scale, but two things degrade gracefully rather than being
# fixed outright:
#   - the index can carry stale entries between listing requests (they're
#     excluded from reads via the now_ms floor, just not deleted yet)
#   - if this ever runs as multiple concurrent worker processes, every
#     worker independently calls purge_expired_index_entries() on each
#     list_redirects() call -- harmless (ZREMRANGEBYSCORE is atomic/
#     idempotent) but redundant work.
#
# If this ever needs a dedicated periodic sweep instead (e.g. to bound
# index size when listings are rare), add an asyncio background task in the
# app's lifespan (see app/main.py) guarded by a SETNX lock so only one
# worker process runs it per interval:
#
#   CLEANUP_LOCK_KEY = "lock:sh:index:cleanup"
#   CLEANUP_INTERVAL_SECONDS = 3600
#
#   async def index_cleanup_loop(client: redis.Redis) -> None:
#       while True:
#           try:
#               # NX: only one worker acquires the lock per interval; EX
#               # bounds how long it's held even if this process dies.
#               acquired = client.set(
#                   CLEANUP_LOCK_KEY, "1", nx=True, ex=CLEANUP_INTERVAL_SECONDS - 60
#               )
#               if acquired:
#                   removed = purge_expired_index_entries(client, time.time() * 1000)
#                   logger.info("Purged %d stale index entries", removed)
#           except redis.RedisError as exc:
#               logger.warning("Index cleanup failed: %s", exc)
#           await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
#
#   # in app/main.py's lifespan:
#   task = asyncio.create_task(index_cleanup_loop(get_redis_client()))
#   yield
#   task.cancel()
#   get_redis_client().close()
def get_index_page(client: redis.Redis, now_ms: float, offset: int, limit: int) -> list[str]:
    """Return one page of non-expired codes from the listing index.

    Args:
        client: The Redis/Valkey client to query.
        now_ms: The current time in milliseconds since epoch.
        offset: The number of matching codes to skip.
        limit: The maximum number of codes to return.

    Returns:
        Up to ``limit`` codes scored >= now_ms, ordered by score
        (soonest-expiring first; permanent codes, scored +inf, last).
    """
    return client.zrangebyscore(SHORT_CODE_INDEX_KEY, now_ms, "+inf", start=offset, num=limit)
