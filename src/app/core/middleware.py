"""HTTP middleware shared across the application."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger
from app.core.responses import app_error_response
from app.core.security import extract_bearer_token, is_valid_api_token

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
    """Protect ``/api/*`` routes with a bearer-token check.

    Requests to any path under :data:`API_PATH_PREFIX` must carry an
    ``Authorization: Bearer <token>`` header matching the configured
    ``API_TOKEN``. All other paths pass through untouched.

    Args:
        request: The incoming HTTP request.
        call_next: The next handler in the middleware chain.

    Returns:
        The unified JSON error response (401) when the token is missing or
        invalid; otherwise the downstream handler's response.
    """
    if request.url.path.startswith(API_PATH_PREFIX):
        settings = get_settings()
        token = extract_bearer_token(request.headers.get("authorization"))

        if not is_valid_api_token(token, settings.api_token):
            auth_logger.warning("Rejected unauthenticated request to %s", request.url.path)
            return app_error_response(UnauthorizedError())

    return await call_next(request)
