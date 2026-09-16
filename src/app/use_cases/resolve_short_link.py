"""Use-case: resolve a short code (and optional variant) to a target URL."""

from __future__ import annotations

import redis

from app.core.codes import is_valid_code_format, is_valid_variant_format
from app.core.config import Settings
from app.core.errors import InvalidShortCodeError, InvalidVariantError
from app.services.redis_client import get_short_link_urls


def resolve_short_link(
    code: str,
    variant: str | None,
    *,
    redis_client: redis.Redis,
    settings: Settings,
) -> str:
    """Resolve a short code to the URL it should redirect to.

    Resolution order: the variant-specific URL (if a variant was given and
    is stored), then the base code's URL, then the configured default URL.

    Args:
        code: The short code extracted from the request path.
        variant: The optional variant string from the ``variant`` query
            parameter, or None if not supplied.
        redis_client: Client used to look up stored redirect targets.
        settings: Application settings, providing the default redirect URL.

    Returns:
        The URL to redirect the client to.

    Raises:
        InvalidShortCodeError: If ``code`` doesn't match the expected
            format of a generated short code.
        InvalidVariantError: If ``variant`` is supplied but doesn't match
            the expected format (1-10 letters).
    """
    if not is_valid_code_format(code):
        raise InvalidShortCodeError(f"'{code}' is not a valid short code.")

    if variant is not None and not is_valid_variant_format(variant):
        raise InvalidVariantError(f"'{variant}' is not a valid variant.")

    variant_url, base_url = get_short_link_urls(redis_client, code, variant)

    return variant_url or base_url or settings.default_redirect_url
