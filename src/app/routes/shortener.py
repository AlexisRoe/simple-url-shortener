"""Public short-link resolution route (``/sh/{code}``)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.services.redis_client import get_redis_client
from app.use_cases.resolve_short_link import resolve_short_link

router = APIRouter(tags=["shortener"])


@router.get("/sh/{code}", summary="Resolve a short code to its target URL")
def resolve_short_code(code: str, variant: str | None = None) -> RedirectResponse:
    """Resolve a short code and redirect to its target URL.

    Args:
        code: The short code to resolve.
        variant: Optional variant string selecting an A/B-tested target
            URL stored alongside the base code.

    Returns:
        A redirect to the resolved target URL: the variant's URL if one
        was requested and stored, otherwise the base code's URL,
        otherwise the configured default redirect URL.

    Raises:
        InvalidShortCodeError: If ``code`` isn't a validly formatted
            short code.
        InvalidVariantError: If ``variant`` is supplied but invalid.
    """
    url = resolve_short_link(
        code,
        variant,
        redis_client=get_redis_client(),
        settings=get_settings(),
    )
    return RedirectResponse(url, status_code=302)
