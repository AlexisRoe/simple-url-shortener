"""FastAPI application factory and entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    API_PATH_PREFIX,
    add_request_id,
    limit_request_body_size,
    log_requests,
    require_api_token,
)
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
        description=(
            "A small, self-hosted URL shortener. Create short codes that "
            "302-redirect to a target URL (`POST /api`, `GET /sh/{code}`), "
            "optionally with several variants of the same code that "
            "resolve to different URLs depending on a `?variant=` query "
            "parameter -- e.g. one short link serving different "
            "audiences or locales rather than a public link-shrinking "
            "service."
        ),
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "health",
                "description": (
                    "Liveness/readiness probes and app/dependency status, for orchestrators and monitoring."
                ),
            },
            {
                "name": "shortener",
                "description": "Public short-code resolution -- redirects a short code to its target URL.",
            },
            {
                "name": "redirect",
                "description": (
                    "Management API -- create, read, update and delete redirects. Bearer-token protected."
                ),
            },
        ],
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

    def custom_openapi() -> dict:
        """Document the ``/api/*`` bearer-token requirement enforced by :func:`require_api_token`.

        That check runs in HTTP middleware rather than as a FastAPI
        ``Security`` dependency (it needs to inspect the raw path prefix
        and attach role/expiry to ``request.state`` before routing), so
        FastAPI can't infer it automatically -- it has to be added to the
        generated schema by hand.
        """
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "description": (
                "One of three configured tokens (read / read_write / delete), sent as "
                "`Authorization: Bearer <token>`. The token's role must cover the "
                "request's HTTP method (read: GET; read_write: GET/POST/PATCH; "
                "delete: all methods) and must not be past its expiry -- see "
                "`GET /api/whoami` to check a token's role and remaining validity."
            ),
        }
        for path, methods in schema.get("paths", {}).items():
            if not path.startswith(API_PATH_PREFIX):
                continue
            for operation in methods.values():
                operation["security"] = [{"bearerAuth": []}]

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app


app = create_app()
