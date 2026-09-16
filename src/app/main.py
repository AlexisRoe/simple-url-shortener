"""FastAPI application factory and entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import log_requests, require_api_token
from app.core.responses import app_error_response
from app.routes import api, ping, shortener, status

logger = get_logger("main")


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
    )

    app.middleware("http")(log_requests)
    app.middleware("http")(require_api_token)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Translate any :class:`AppError` into a unified JSON error response."""
        logger.error("%s: %s", exc.code, exc.message)
        return app_error_response(exc)

    app.include_router(ping.router)
    app.include_router(status.router)
    app.include_router(shortener.router)
    app.include_router(api.router)

    return app


app = create_app()
