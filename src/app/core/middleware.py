"""HTTP middleware shared across the application."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.config import get_settings
from app.core.errors import InsufficientScopeError, TokenExpiredError, UnauthorizedError
from app.core.logging import get_logger
from app.core.responses import app_error_response
from app.core.security import extract_bearer_token, required_role_for_method, resolve_token

logger = get_logger("http")
auth_logger = get_logger("auth")

API_PATH_PREFIX = "/api"


async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Log every request handled by the server in a single, unified line.

    Args:
        request: The incoming HTTP request.
        call_next: The next handler in the middleware chain.

    Returns:
        The response produced by the downstream handler, unmodified.
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.2fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


async def require_api_token(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Protect ``/api/*`` routes with a scoped, expiring bearer-token check.

    Requests to any path under :data:`API_PATH_PREFIX` must carry an
    ``Authorization: Bearer <token>`` header matching one of the three
    configured tokens (read / read_write / delete). The matched token's
    role must cover the request's HTTP method (see
    :func:`app.core.security.required_role_for_method`) and must not have
    expired. On success, the resolved role and expiry are attached to
    ``request.state`` for downstream use (e.g. the ``/api/whoami`` route).
    All other paths pass through untouched.

    Args:
        request: The incoming HTTP request.
        call_next: The next handler in the middleware chain.

    Returns:
        The unified JSON error response (401/403) when the token is
        missing, invalid, expired, or under-scoped; otherwise the
        downstream handler's response.
    """
    if request.url.path.startswith(API_PATH_PREFIX):
        settings = get_settings()
        token = extract_bearer_token(request.headers.get("authorization"))
        matched = resolve_token(token, settings)

        if matched is None:
            auth_logger.warning(
                "Rejected %s %s: missing or unrecognized token", request.method, request.url.path
            )
            return app_error_response(UnauthorizedError())

        if matched.is_expired:
            auth_logger.warning(
                "Rejected %s %s: %s token expired at %s",
                request.method,
                request.url.path,
                matched.role.name.lower(),
                matched.expires_at.isoformat(),
            )
            return app_error_response(TokenExpiredError())

        required_role = required_role_for_method(request.method)

        if matched.role < required_role:
            auth_logger.warning(
                "Rejected %s %s: %s token lacks required %s scope",
                request.method,
                request.url.path,
                matched.role.name.lower(),
                required_role.name.lower(),
            )
            return app_error_response(InsufficientScopeError())

        auth_logger.info(
            "Authorized %s %s using %s token (expires %s)",
            request.method,
            request.url.path,
            matched.role.name.lower(),
            matched.expires_at.isoformat(),
        )
        request.state.token_role = matched.role
        request.state.token_expires_at = matched.expires_at

    return await call_next(request)
