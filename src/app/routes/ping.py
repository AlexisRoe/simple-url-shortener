"""Ping route: a minimal liveness check."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get(
    "/ping",
    response_model=str,
    summary="Liveness check",
    responses={200: {"content": {"application/json": {"example": "pong"}}}},
)
def ping() -> str:
    """Confirm the server process is alive and handling requests.

    Returns:
        The literal string ``"pong"``.
    """
    return "pong"
