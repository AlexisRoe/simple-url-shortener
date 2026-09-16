"""Shared request-field validation for the redirect CRUD use-cases."""

from __future__ import annotations

from app.core.errors import InsecureUrlError, InvalidTtlError, InvalidUrlError
from app.core.urls import is_insecure_http_url, is_valid_ttl_ms, is_valid_url


def validate_url(url: str) -> None:
    """Validate a redirect target URL, raising a specific error per failure.

    Args:
        url: The candidate redirect target URL.

    Raises:
        InsecureUrlError: If ``url`` is an otherwise well-formed plain
            http URL.
        InvalidUrlError: If ``url`` isn't a valid absolute https URL.
    """
    if is_valid_url(url):
        return

    if is_insecure_http_url(url):
        raise InsecureUrlError(f"'{url}' uses http; only https URLs are allowed.")

    raise InvalidUrlError(f"'{url}' is not a valid URL.")


def validate_ttl(ttl: int | None) -> None:
    """Validate a TTL in milliseconds.

    Args:
        ttl: The candidate TTL in milliseconds, or None for no expiry.

    Raises:
        InvalidTtlError: If ``ttl`` is supplied but isn't a positive integer.
    """
    if not is_valid_ttl_ms(ttl):
        raise InvalidTtlError(f"'{ttl}' is not a valid TTL in milliseconds.")
