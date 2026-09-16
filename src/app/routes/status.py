"""Status route: reports application and dependency health."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.services.redis_client import check_redis_connection

router = APIRouter(tags=["health"])


class StatusResponse(BaseModel):
    """Response payload for the ``/status`` endpoint."""

    name: str
    version: str
    date: str
    status: str
    redis_connected: bool


@router.get("/status", response_model=StatusResponse, summary="Application and dependency status")
def get_status(settings: Settings = Depends(get_settings)) -> StatusResponse:
    """Report the application's identity, current time, and dependency health.

    Args:
        settings: Injected, validated application settings.

    Returns:
        A :class:`StatusResponse` describing the app name/version, the
        current UTC timestamp, overall status, and the Redis/Valkey
        connection health.
    """
    redis_connected = check_redis_connection()
    return StatusResponse(
        name=settings.app_name,
        version=settings.app_version,
        date=datetime.now(UTC).isoformat(),
        status="ok" if redis_connected else "degraded",
        redis_connected=redis_connected,
    )
