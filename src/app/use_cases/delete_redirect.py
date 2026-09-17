"""Use-case: delete a single redirect entry (a code, or a code+variant)."""

from __future__ import annotations

import redis

from app.core.errors import RedirectNotFoundError
from app.core.logging import get_logger
from app.services.redis_client import build_short_link_key, delete_key, key_exists, remove_code_from_index

logger = get_logger("delete_redirect")


def delete_redirect(*, redis_client: redis.Redis, code: str, variant: str | None) -> None:
    """Delete a single redirect entry.

    Args:
        redis_client: Client used to check existence and delete the entry.
        code: The short code identifying the redirect.
        variant: The optional variant identifying a specific entry under
            ``code``. None targets the base code's entry.

    Raises:
        RedirectNotFoundError: If the targeted entry doesn't exist.
    """
    key = build_short_link_key(code, variant)

    if not key_exists(redis_client, key):
        logger.warning("Attempted to delete missing entry %r", key)
        raise RedirectNotFoundError(f"Redirect '{key}' does not exist.")

    delete_key(redis_client, key)

    if variant is None:
        remove_code_from_index(redis_client, code)

    logger.info("Deleted entry %r", key)
