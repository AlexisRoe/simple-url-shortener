"""Redirect target URL format validation."""

from __future__ import annotations

from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """Check that ``url`` is an absolute https URL.

    Query parameters, if present, are part of the URL and don't need any
    special handling here since :func:`urllib.parse.urlparse` already
    accounts for them.

    Args:
        url: The candidate redirect target URL.

    Returns:
        True if ``url`` has an ``https`` scheme and a host.
    """
    parsed = urlparse(url)

    return parsed.scheme == "https" and bool(parsed.netloc)


def is_insecure_http_url(url: str) -> bool:
    """Check whether ``url`` is an otherwise well-formed plain http URL.

    Used to give http URLs a specific, actionable error rather than the
    generic "invalid URL" error.

    Args:
        url: The candidate redirect target URL.

    Returns:
        True if ``url`` has an ``http`` scheme and a host.
    """
    parsed = urlparse(url)

    return parsed.scheme == "http" and bool(parsed.netloc)


def is_valid_ttl_ms(ttl: object) -> bool:
    """Check that ``ttl`` is either absent or a positive integer.

    Non-integer numeric types (e.g. ``float``) are rejected, since a TTL
    must be a whole number of milliseconds.

    Args:
        ttl: The candidate TTL in milliseconds, or None for no expiry.

    Returns:
        True if ``ttl`` is None or a positive integer.
    """
    if ttl is None:
        return True

    return isinstance(ttl, int) and ttl > 0
