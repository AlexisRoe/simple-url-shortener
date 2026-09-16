"""HTTP middleware shared across the application."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import Request, Response

from app.core.config import get_settings
from app.core.constants import MAX_REQUEST_BODY_BYTES
from app.core.errors import InsufficientScopeError, PayloadTooLargeError, TokenExpiredError, UnauthorizedError
from app.core.logging import get_logger
from app.core.request_context import generate_request_id, reset_request_id, set_request_id
from app.core.responses import app_error_response
from app.core.security import extract_bearer_token, required_role_for_method, resolve_token

logger = get_logger("http")
auth_logger = get_logger("auth")

API_PATH_PREFIX = "/api"
REQUEST_ID_HEADER = "X-Request-ID"


async def limit_request_body_size(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Reject request bodies larger than :data:`MAX_REQUEST_BODY_BYTES`.

    Every body this app expects is a small JSON object (a URL string and
    an optional TTL/variant), so anything past the configured limit is
    rejected before it reaches route handlers. Caddy enforces the same
    limit at the edge (see ``infra/caddy/snippets/security-headers.caddy``);
    this is a second, independent check for requests that reach the app
    directly (e.g. local development without Caddy in front).

    Checks the declared ``Content-Length`` first as a cheap early
    rejection, then falls back to counting bytes as the body is actually
    read, since a client can omit ``Content-Length`` or send chunked
    transfer-encoding.

    Args:
        request: The incoming HTTP request.
        call_next: The next handler in the middleware chain.

    Returns:
        A 413 error response if the body is too large, otherwise the
        downstream handler's response.
    """
    content_length = request.headers.get("content-length")
    declared_size = int(content_length) if content_length is not None and content_length.isdigit() else None
    if declared_size is not None and declared_size > MAX_REQUEST_BODY_BYTES:
        logger.warning(
            "Rejected %s %s: declared Content-Length %s exceeds %d bytes",
            request.method,
            request.url.path,
            content_length,
            MAX_REQUEST_BODY_BYTES,
        )
        return app_error_response(PayloadTooLargeError())

    original_stream = request.stream
    seen_bytes = 0

    async def limited_stream() -> AsyncIterator[bytes]:
        nonlocal seen_bytes
        async for chunk in original_stream():
            seen_bytes += len(chunk)
            if seen_bytes > MAX_REQUEST_BODY_BYTES:
                logger.warning(
                    "Rejected %s %s: streamed body exceeds %d bytes",
                    request.method,
                    request.url.path,
                    MAX_REQUEST_BODY_BYTES,
                )
                raise PayloadTooLargeError()
            yield chunk

    request.stream = limited_stream  # type: ignore[method-assign]

    try:
        return await call_next(request)
    except PayloadTooLargeError as exc:
        return app_error_response(exc)


# No metrics/tracing hooks yet (e.g. Prometheus /metrics or OpenTelemetry
# spans exporting request rate, latency percentiles, error rate). Deemed
# overkill for this app's current scope; log_requests below already
# computes per-request duration_ms, which would be the natural value to
# also export as a histogram if/when this is added. See README.md.


async def add_request_id(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Correlate every log line emitted while handling a request.

    Uses the incoming ``X-Request-ID`` header if the caller supplied one
    (useful when this service sits behind another that already assigns
    one), otherwise generates a new one. The ID is stashed on
    ``request.state``, bound to a contextvar so every log call made
    downstream picks it up automatically (see
    :mod:`app.core.request_context`), and echoed back in the response so
    the caller can correlate their own logs against it too.

    Args:
        request: The incoming HTTP request.
        call_next: The next handler in the middleware chain.

    Returns:
        The downstream response, with the request ID attached as an
        ``X-Request-ID`` header.
    """
    request_id = request.headers.get(REQUEST_ID_HEADER) or generate_request_id()
    request.state.request_id = request_id
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        reset_request_id(token)

    response.headers[REQUEST_ID_HEADER] = request_id
    return response


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
