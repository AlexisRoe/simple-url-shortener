"""Use-case: list all short-link redirects, grouped by code, with pagination."""

from __future__ import annotations

from dataclasses import dataclass, field

import redis

from app.core.constants import SHORT_CODE_KEY_PREFIX
from app.core.logging import get_logger
from app.services.redis_client import get_key_values_and_ttls, scan_short_link_keys

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


def list_redirects(*, redis_client: redis.Redis, page: int, page_size: int) -> RedirectPage:
    """List all short-link redirects, grouped by code, with pagination.

    Every ``sh:*`` key is scanned and grouped by short code: the base key
    (``sh:<code>``) holds a redirect's primary URL, and any
    ``sh:<code>:<variant>`` keys hold its variant URLs. Each URL's TTL is
    reported as stored in Redis (``-1`` if the key has no expiry).

    Pagination is applied in-memory over the codes sorted alphabetically,
    since Redis has no native way to page over grouped keys.

    Args:
        redis_client: Client used to scan and fetch stored redirects.
        page: The 1-indexed page number to return.
        page_size: The maximum number of redirects per page.

    Returns:
        The requested page of redirects, plus the total redirect count.
    """
    keys = scan_short_link_keys(redis_client)
    values, ttls = get_key_values_and_ttls(redis_client, keys)

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

    codes = sorted(redirects)
    total = len(codes)

    start = (page - 1) * page_size
    page_codes = codes[start : start + page_size]
    items = [redirects[code] for code in page_codes]

    logger.info(
        "Listed %d redirect(s) (page=%d, page_size=%d, total=%d)",
        len(items),
        page,
        page_size,
        total,
    )

    return RedirectPage(items=items, total=total, page=page, page_size=page_size)
