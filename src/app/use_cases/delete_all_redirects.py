"""Use-case: delete a code's entry and all of its variants at once."""

from __future__ import annotations

import redis

from app.core.errors import RedirectNotFoundError
from app.core.logging import get_logger
from app.services.redis_client import (
    build_short_link_key,
    delete_keys,
    key_exists,
    remove_code_from_index,
    scan_keys_for_code,
)

logger = get_logger("delete_all_redirects")


def delete_all_redirects(*, redis_client: redis.Redis, code: str) -> None:
    """Delete a short code's base entry and all of its variant entries.

    Args:
        redis_client: Client used to scan and delete the code's keys.
        code: The short code whose entries should all be deleted.

    Raises:
        RedirectNotFoundError: If ``code`` doesn't exist.
    """
    if not key_exists(redis_client, build_short_link_key(code)):
        logger.warning("Attempted to delete all entries for missing code %r", code)
        raise RedirectNotFoundError(f"Redirect '{code}' does not exist.")

    keys = scan_keys_for_code(redis_client, code)
    delete_keys(redis_client, keys)
    remove_code_from_index(redis_client, code)
    logger.info("Deleted code %r and %d variant(s)", code, len(keys) - 1)
