"""Use-case: create a variant URL for an existing short code."""

from __future__ import annotations

from dataclasses import dataclass

import redis

from app.core.codes import is_valid_variant_format
from app.core.errors import InvalidVariantError, RedirectNotFoundError
from app.core.logging import get_logger
from app.services.redis_client import (
    build_short_link_key,
    get_key_values_and_ttls,
    key_exists,
    set_short_link,
)
from app.use_cases.validation import validate_ttl, validate_url

logger = get_logger("create_variant")


@dataclass
class CreatedVariant:
    """A newly created variant, including its parent code for context."""

    code: str
    variant: str
    url: str
    ttl: int


def create_variant(
    *, redis_client: redis.Redis, code: str, variant: str, url: str, ttl: int | None
) -> CreatedVariant:
    """Create a variant URL under an existing short code.

    Args:
        redis_client: Client used to check the code exists and write the
            new variant entry.
        code: The short code the variant belongs to. Must already exist.
        variant: The variant string identifying this entry.
        url: The redirect target URL. Must be an absolute https URL.
        ttl: The optional expiry in milliseconds. None means the entry
            never expires.

    Returns:
        The newly created variant.

    Raises:
        RedirectNotFoundError: If ``code`` doesn't exist.
        InvalidVariantError: If ``variant`` fails format validation.
        InsecureUrlError: If ``url`` uses plain http instead of https.
        InvalidUrlError: If ``url`` isn't a valid absolute https URL.
        InvalidTtlError: If ``ttl`` is supplied but isn't a positive integer.
    """
    base_key = build_short_link_key(code)

    if not key_exists(redis_client, base_key):
        logger.warning("Attempted to create variant on missing code %r", code)
        raise RedirectNotFoundError(f"Redirect '{code}' does not exist.")

    if not is_valid_variant_format(variant):
        logger.warning("Invalid variant format for code %r: %r", code, variant)
        raise InvalidVariantError(f"'{variant}' is not a valid variant.")

    validate_url(url)
    validate_ttl(ttl)

    variant_key = build_short_link_key(code, variant)
    set_short_link(redis_client, variant_key, url, ttl)

    ([_], [actual_ttl]) = get_key_values_and_ttls(redis_client, [variant_key])
    logger.info("Created variant %r for code %r", variant, code)

    return CreatedVariant(code=code, variant=variant, url=url, ttl=actual_ttl)
