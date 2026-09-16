"""Bearer-token authentication helpers for the internal API."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum

from app.core.config import Settings


class Role(IntEnum):
    """Access scopes, ordered so a higher role satisfies a lower requirement.

    A ``DELETE``-scoped token can also perform reads and writes; a
    ``READ``-scoped token can only read.
    """

    READ = 1
    READ_WRITE = 2
    DELETE = 3


# HTTP methods that mutate data outside of deleting it (create/update).
_WRITE_METHODS = {"POST", "PATCH", "PUT"}


def required_role_for_method(method: str) -> Role:
    """Determine the minimum :class:`Role` an endpoint's HTTP method requires.

    Args:
        method: The request's HTTP method (e.g. "GET", "POST", "DELETE").

    Returns:
        ``Role.DELETE`` for ``DELETE`` requests, ``Role.READ_WRITE`` for
        requests that create or modify data, ``Role.READ`` otherwise.
    """
    if method == "DELETE":
        return Role.DELETE

    if method in _WRITE_METHODS:
        return Role.READ_WRITE

    return Role.READ


@dataclass(frozen=True)
class TokenInfo:
    """The resolved identity of a successfully-matched bearer token."""

    role: Role
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Whether this token's expiry has passed."""
        return datetime.now(UTC) >= self.expires_at


def resolve_token(token: str | None, settings: Settings) -> TokenInfo | None:
    """Match a bearer token against the three configured scoped tokens.

    Args:
        token: The token extracted from the request, or ``None``.
        settings: The application settings holding the three configured
            tokens and their expiries.

    Returns:
        The matching :class:`TokenInfo` (which may already be expired --
        callers must check :attr:`TokenInfo.is_expired`), or ``None`` if
        ``token`` doesn't match any configured token.
    """
    if token is None:
        return None

    candidates = (
        (settings.api_token_read, Role.READ, settings.api_token_read_expires_at),
        (settings.api_token_read_write, Role.READ_WRITE, settings.api_token_read_write_expires_at),
        (settings.api_token_delete, Role.DELETE, settings.api_token_delete_expires_at),
    )

    for expected_token, role, expires_at in candidates:
        if hmac.compare_digest(token, expected_token):
            return TokenInfo(role=role, expires_at=expires_at)

    return None


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
