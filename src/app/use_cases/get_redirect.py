"""Use-case: fetch a single redirect (base URL plus any variants) by code."""

from __future__ import annotations

import redis

from app.core.errors import RedirectNotFoundError
from app.core.logging import get_logger
from app.services.redis_client import get_key_values_and_ttls, scan_keys_for_code
from app.use_cases.list_redirects import Redirect, group_redirects_by_code

logger = get_logger("get_redirect")


def get_redirect(*, redis_client: redis.Redis, code: str) -> Redirect:
    """Fetch a single redirect by its short code, including its variants.

    Args:
        redis_client: Client used to scan and fetch the redirect's keys.
        code: The short code to look up.

    Returns:
        The redirect, with its base URL, TTL, and any variants.

    Raises:
        RedirectNotFoundError: If ``code`` doesn't exist.
    """
    keys = scan_keys_for_code(redis_client, code)
    values, ttls = get_key_values_and_ttls(redis_client, keys)
    redirects = group_redirects_by_code(keys, values, ttls)

    redirect = redirects.get(code)

    if redirect is None or redirect.url is None:
        logger.warning("Redirect %r not found", code)
        raise RedirectNotFoundError(f"Redirect '{code}' does not exist.")

    logger.info("Fetched redirect %r", code)
    return redirect
