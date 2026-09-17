"""Status route: reports application and dependency health.

Exposes three related endpoints:

- ``/status`` -- human-facing app identity + dependency snapshot (kept for
  backwards compatibility; not intended for orchestrator probes).
- ``/health/livez`` -- Kubernetes-style liveness probe: process is up and
  can handle HTTP at all. Never checks external dependencies -- a Redis
  outage must not cause an orchestrator to kill and restart this
  container, since restarting it does nothing to fix Redis.
- ``/health/readyz`` -- Kubernetes-style readiness probe: this instance
  can currently serve traffic. Checks Redis, since ``/sh/*`` redirects
  and ``/api/*`` both depend on it; returns 503 when it's unreachable so
  the instance is pulled out of rotation until it recovers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
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

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "simple-url-shortener",
                "version": "1.1.0",
                "date": "2026-09-17T13:08:46.000000+00:00",
                "status": "ok",
                "redis_connected": True,
            }
        }
    }


class HealthResponse(BaseModel):
    """Response payload for the ``/health/*`` probe endpoints."""

    status: str


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Application and dependency status",
)
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


@router.get(
    "/health/livez",
    response_model=HealthResponse,
    summary="Liveness probe",
    responses={200: {"content": {"application/json": {"example": {"status": "ok"}}}}},
)
def get_livez() -> HealthResponse:
    """Report whether the process is alive.

    Deliberately checks nothing external: if this handler can run at all,
    the process is alive. An orchestrator should restart the container
    only when this fails, never when a downstream dependency is degraded.

    Returns:
        ``{"status": "ok"}``, always, as long as the process is running.
    """
    return HealthResponse(status="ok")


@router.get(
    "/health/readyz",
    response_model=HealthResponse,
    summary="Readiness probe",
    responses={
        200: {"content": {"application/json": {"example": {"status": "ok"}}}},
        503: {"content": {"application/json": {"example": {"status": "unavailable"}}}},
    },
)
def get_readyz(response: Response) -> HealthResponse:
    """Report whether this instance is ready to serve traffic.

    Args:
        response: Injected response, used to set a 503 status when not ready.

    Returns:
        ``{"status": "ok"}`` with a 200 when Redis is reachable, otherwise
        ``{"status": "unavailable"}`` with a 503 so the orchestrator/load
        balancer stops routing traffic here until it recovers.
    """
    if check_redis_connection():
        return HealthResponse(status="ok")

    response.status_code = 503
    return HealthResponse(status="unavailable")
