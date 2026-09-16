"""Bearer-token authentication helpers for the internal API."""

from __future__ import annotations

import hmac


def extract_bearer_token(header_value: str | None) -> str | None:
    """Extract the token from an ``Authorization: Bearer <token>`` header.

    Args:
        header_value: The raw value of the ``Authorization`` header, if any.

    Returns:
        The extracted token, or ``None`` if the header is missing, empty,
        or does not use the ``Bearer`` scheme.
    """
    if not header_value:
        return None

    scheme, _, token = header_value.partition(" ")

    if scheme.lower() != "bearer" or not token:
        return None

    return token


def is_valid_api_token(token: str | None, expected_token: str) -> bool:
    """Check a bearer token against the configured API token.

    Uses a constant-time comparison (:func:`hmac.compare_digest`) so the
    check does not leak timing information an attacker could use to guess
    the token byte-by-byte.

    Args:
        token: The token extracted from the request, or ``None``.
        expected_token: The configured API token to compare against.

    Returns:
        True if ``token`` is present and matches ``expected_token``.
    """
    if token is None:
        return False

    return hmac.compare_digest(token, expected_token)
