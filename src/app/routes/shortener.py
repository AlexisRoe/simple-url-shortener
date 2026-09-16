"""Public short-link resolution route (``/sh/{code}``).

This is a stub: the redirect-resolution logic (looking up the code in
Valkey and issuing an HTTP redirect to its target URL) will be built on
top of this route in a follow-up.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import FeatureNotImplementedError

router = APIRouter(tags=["shortener"])


@router.get("/sh/{code}", summary="Resolve a short code to its target URL")
def resolve_short_code(code: str) -> None:
    """Resolve a short code and redirect to its target URL.

    Args:
        code: The short code to resolve.

    Raises:
        FeatureNotImplementedError: Always; redirect resolution is not
            implemented yet.
    """
    raise FeatureNotImplementedError(f"Resolving short code '{code}' is not implemented yet.")
