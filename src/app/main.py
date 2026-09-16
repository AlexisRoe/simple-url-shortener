"""FastAPI application factory and entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import add_request_id, limit_request_body_size, log_requests, require_api_token
from app.core.responses import app_error_response
from app.routes import api, ping, shortener, status
from app.services.redis_client import get_redis_client

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Release shared resources on shutdown.

    The Redis/Valkey client (:func:`get_redis_client`) is a process-wide
    singleton backed by a connection pool; without this, the process would
    exit without releasing its sockets cleanly.
    """
    yield
    get_redis_client().close()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance.

    Loads and validates settings, configures unified logging, registers
    the request-logging middleware, a unified error handler for
    :class:`AppError`, and all routers. OpenAPI docs are only exposed at
    ``/docs`` in the development environment.

    Returns:
        A fully configured :class:`FastAPI` application.
    """
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Registered last so it wraps outermost (Starlette runs the
    # most-recently-added middleware first): the request ID must be bound
    # before log_requests/require_api_token run so their log lines are
    # correlated too.
    app.middleware("http")(limit_request_body_size)
    app.middleware("http")(log_requests)
    app.middleware("http")(require_api_token)
    app.middleware("http")(add_request_id)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Translate any :class:`AppError` into a unified JSON error response."""
        logger.error("%s: %s", exc.code, exc.message)
        return app_error_response(exc)

    @app.exception_handler(404)
    async def handle_not_found(request: Request, exc: HTTPException) -> RedirectResponse:
        """Send requests to unknown paths to the configured default URL.

        Mirrors the fallback behaviour of :func:`resolve_short_link` for
        unknown short codes, so the whole app has one consistent "unknown
        route" experience instead of a bare JSON 404.
        """
        return RedirectResponse(settings.default_redirect_url, status_code=302)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Catch any exception not explicitly handled above.

        Logs the full traceback server-side (never exposed to the client)
        and renders it in the same unified error shape as :class:`AppError`,
        so API clients never see a bare unhandled-exception response.
        """
        logger.exception("Unhandled %s: %s", type(exc).__name__, exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Internal server error."}},
        )

    app.include_router(ping.router)
    app.include_router(status.router)
    app.include_router(shortener.router)
    app.include_router(api.router)

    return app


app = create_app()
