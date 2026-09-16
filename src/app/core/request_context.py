"""Per-request context propagated implicitly through log calls.

Uses a :class:`contextvars.ContextVar` so the current request's ID is
available to any log call made while handling that request, without
threading it through every function signature. Each ``await`` boundary in
asyncio copies the context, so this stays correctly isolated per request
even under concurrent requests.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Generate a new random request ID."""
    return uuid.uuid4().hex


def set_request_id(value: str) -> Token[str | None]:
    """Bind ``value`` as the current request's ID.

    Args:
        value: The request ID to bind (generated, or taken from an
            incoming ``X-Request-ID`` header).

    Returns:
        A token that can be passed to :func:`reset_request_id` to restore
        the previous value.
    """
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    """Undo a prior :func:`set_request_id` call, restoring the previous value.

    Args:
        token: The token returned by the corresponding :func:`set_request_id` call.
    """
    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the current request's ID, or ``None`` outside a request context."""
    return _request_id.get()
