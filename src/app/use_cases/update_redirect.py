"""Use-case: update an existing redirect (a code, or a code+variant) entry."""

from __future__ import annotations

from dataclasses import dataclass

import redis

from app.core.codes import is_valid_variant_format
from app.core.errors import InvalidVariantError, RedirectNotFoundError
from app.core.logging import get_logger
from app.services.redis_client import (
    add_code_to_index,
    build_short_link_key,
    get_key_values_and_ttls,
    key_exists,
    set_short_link,
)
from app.use_cases.validation import validate_ttl, validate_url

logger = get_logger("update_redirect")


@dataclass
class UpdatedRedirect:
    """A single updated entry: either a base code or a code+variant."""

    code: str
    variant: str | None
    url: str
    ttl: int


def update_redirect(
    *, redis_client: redis.Redis, code: str, variant: str | None, url: str, ttl: int | None
) -> UpdatedRedirect:
    """Update a single existing redirect entry.

    Exactly one entry is updated: the base code's entry if ``variant`` is
    None, otherwise the specific code+variant entry.

    Args:
        redis_client: Client used to check existence and write the update.
        code: The short code identifying the redirect.
        variant: The optional variant identifying a specific entry under
            ``code``. None targets the base code's entry.
        url: The new redirect target URL. Must be an absolute https URL.
        ttl: The optional new expiry in milliseconds. None means the
            entry never expires.

    Returns:
        The updated entry.

    Raises:
        InvalidVariantError: If ``variant`` is supplied but fails format
            validation.
        InsecureUrlError: If ``url`` uses plain http instead of https.
        InvalidUrlError: If ``url`` isn't a valid absolute https URL.
        InvalidTtlError: If ``ttl`` is supplied but isn't a positive integer.
        RedirectNotFoundError: If the targeted entry doesn't exist.
    """
    if variant is not None and not is_valid_variant_format(variant):
        logger.warning("Invalid variant format for code %r: %r", code, variant)
        raise InvalidVariantError(f"'{variant}' is not a valid variant.")

    validate_url(url)
    validate_ttl(ttl)

    key = build_short_link_key(code, variant)

    if not key_exists(redis_client, key):
        logger.warning("Attempted to update missing entry %r", key)
        raise RedirectNotFoundError(f"Redirect '{key}' does not exist.")

    set_short_link(redis_client, key, url, ttl)

    if variant is None:
        add_code_to_index(redis_client, code, ttl)

    ([_], [actual_ttl]) = get_key_values_and_ttls(redis_client, [key])
    logger.info("Updated entry %r", key)

    return UpdatedRedirect(code=code, variant=variant, url=url, ttl=actual_ttl)
