"""Use-case: create a new short-link redirect."""

from __future__ import annotations

import redis

from app.core.logging import get_logger
from app.services.redis_client import (
    add_code_to_index,
    build_short_link_key,
    get_key_values_and_ttls,
    set_short_link,
)
from app.use_cases.codes import generate_unique_code
from app.use_cases.list_redirects import Redirect
from app.use_cases.validation import validate_ttl, validate_url

logger = get_logger("create_redirect")


def create_redirect(*, redis_client: redis.Redis, url: str, ttl: int | None) -> Redirect:
    """Create a new redirect under a freshly generated short code.

    Args:
        redis_client: Client used to check for code collisions and write
            the new entry.
        url: The redirect target URL. Must be an absolute https URL.
        ttl: The optional expiry in milliseconds. None means the entry
            never expires.

    Returns:
        The newly created redirect.

    Raises:
        InsecureUrlError: If ``url`` uses plain http instead of https.
        InvalidUrlError: If ``url`` isn't a valid absolute https URL.
        InvalidTtlError: If ``ttl`` is supplied but isn't a positive integer.
    """
    validate_url(url)
    validate_ttl(ttl)

    code = generate_unique_code(redis_client)
    key = build_short_link_key(code)
    set_short_link(redis_client, key, url, ttl)
    add_code_to_index(redis_client, code, ttl)

    ([_], [actual_ttl]) = get_key_values_and_ttls(redis_client, [key])
    logger.info("Created redirect %r", code)

    return Redirect(code=code, url=url, ttl=actual_ttl, variants=[])
