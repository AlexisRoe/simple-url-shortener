"""Use-case: list all short-link redirects, grouped by code, with pagination."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import redis

from app.core.constants import SHORT_CODE_KEY_PREFIX
from app.core.logging import get_logger
from app.services.redis_client import (
    get_index_count,
    get_index_page,
    get_key_values_and_ttls,
    purge_expired_index_entries,
    scan_keys_for_code,
)

logger = get_logger("list_redirects")


@dataclass
class VariantRedirect:
    """A single variant URL belonging to a redirect."""

    variant: str
    url: str
    ttl: int


@dataclass
class Redirect:
    """A redirect: its base code, primary URL, and any variant URLs."""

    code: str
    url: str | None
    ttl: int
    variants: list[VariantRedirect] = field(default_factory=list)


@dataclass
class RedirectPage:
    """A page of redirects plus pagination metadata."""

    items: list[Redirect]
    total: int
    page: int
    page_size: int


def group_redirects_by_code(
    keys: list[str], values: list[str | None], ttls: list[int]
) -> dict[str, Redirect]:
    """Group parallel key/value/ttl lists into :class:`Redirect` objects by code.

    The base key (``sh:<code>``) holds a redirect's primary URL, and any
    ``sh:<code>:<variant>`` keys hold its variant URLs. Keys whose value is
    None (e.g. expired between scan and fetch) are skipped.

    Args:
        keys: The scanned Redis keys.
        values: The value of each key, parallel to ``keys``.
        ttls: The TTL of each key, parallel to ``keys``.

    Returns:
        A mapping of short code to its grouped :class:`Redirect`.
    """
    prefix = f"{SHORT_CODE_KEY_PREFIX}:"
    redirects: dict[str, Redirect] = {}

    for key, value, ttl in zip(keys, values, ttls, strict=True):
        if value is None:
            continue

        remainder = key[len(prefix) :]
        parts = remainder.split(":", 1)
        code = parts[0]
        redirect = redirects.setdefault(code, Redirect(code=code, url=None, ttl=-1))

        if len(parts) == 1:
            redirect.url = value
            redirect.ttl = ttl
        else:
            redirect.variants.append(VariantRedirect(variant=parts[1], url=value, ttl=ttl))

    return redirects


def list_redirects(*, redis_client: redis.Redis, page: int, page_size: int) -> RedirectPage:
    """List short-link redirects, grouped by code, with pagination.

    Codes are paginated via a secondary ZSET index (``sh:index``) of base
    codes, scored by expiry timestamp, so this only touches the keyspace
    for the codes on the requested page rather than scanning every ``sh:*``
    key. Only the page's codes are then scanned (base + variant keys) and
    grouped: the base key (``sh:<code>``) holds a redirect's primary URL,
    and any ``sh:<code>:<variant>`` keys hold its variant URLs. Each URL's
    TTL is reported as stored in Redis (``-1`` if the key has no expiry).

    Results are ordered by the index's score (soonest-expiring codes
    first, permanent codes last), not alphabetically.

    Args:
        redis_client: Client used to read the index and fetch stored
            redirects.
        page: The 1-indexed page number to return.
        page_size: The maximum number of redirects per page.

    Returns:
        The requested page of redirects, plus the total redirect count.
    """
    now_ms = time.time() * 1000
    purge_expired_index_entries(redis_client, now_ms)

    total = get_index_count(redis_client, now_ms)
    offset = (page - 1) * page_size
    page_codes = get_index_page(redis_client, now_ms, offset, page_size)

    keys = [key for code in page_codes for key in scan_keys_for_code(redis_client, code)]
    values, ttls = get_key_values_and_ttls(redis_client, keys)
    redirects = group_redirects_by_code(keys, values, ttls)

    items = [redirects[code] for code in page_codes if code in redirects]

    logger.info(
        "Listed %d redirect(s) (page=%d, page_size=%d, total=%d)",
        len(items),
        page,
        page_size,
        total,
    )

    return RedirectPage(items=items, total=total, page=page, page_size=page_size)
