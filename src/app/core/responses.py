"""Shared helpers for turning application errors into HTTP responses."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from app.core.errors import AppError


def app_error_response(exc: AppError) -> JSONResponse:
    """Render an :class:`AppError` as the application's unified JSON error shape.

    Args:
        exc: The application error to render.

    Returns:
        A :class:`JSONResponse` with the error's status code and a body of
        the form ``{"error": {"code": ..., "message": ...}}``.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
