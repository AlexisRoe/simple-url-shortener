"""Redirect management routes (``/api``).

Covers full CRUD for a single redirect plus an overview listing of all
existing redirects. All routes here live under ``/api`` and are therefore
protected by the bearer-token auth middleware
(:func:`app.core.middleware.require_api_token`).

These are stubs: the persistence layer (backed by Valkey) will be
implemented in a follow-up.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import FeatureNotImplementedError

router = APIRouter(prefix="/api", tags=["redirect"])


@router.get("", summary="List all redirects")
def list_redirects() -> None:
    """Return an overview of all existing redirects.

    Raises:
        FeatureNotImplementedError: Always; persistence is not implemented yet.
    """
    raise FeatureNotImplementedError("Listing redirects is not implemented yet.")


@router.post("", summary="Create a redirect", status_code=201)
def create_redirect() -> None:
    """Create a new shortened-URL redirect.

    Raises:
        FeatureNotImplementedError: Always; persistence is not implemented yet.
    """
    raise FeatureNotImplementedError("Creating a redirect is not implemented yet.")


@router.get("/{code}", summary="Get a single redirect")
def get_redirect(code: str) -> None:
    """Fetch a single redirect by its short code.

    Args:
        code: The short code identifying the redirect.

    Raises:
        FeatureNotImplementedError: Always; persistence is not implemented yet.
    """
    raise FeatureNotImplementedError(f"Fetching redirect '{code}' is not implemented yet.")


@router.patch("/{code}", summary="Update a single redirect")
def update_redirect(code: str) -> None:
    """Update a single redirect by its short code.

    Args:
        code: The short code identifying the redirect.

    Raises:
        FeatureNotImplementedError: Always; persistence is not implemented yet.
    """
    raise FeatureNotImplementedError(f"Updating redirect '{code}' is not implemented yet.")


@router.delete("/{code}", summary="Delete a single redirect", status_code=204)
def delete_redirect(code: str) -> None:
    """Delete a single redirect by its short code.

    Args:
        code: The short code identifying the redirect.

    Raises:
        FeatureNotImplementedError: Always; persistence is not implemented yet.
    """
    raise FeatureNotImplementedError(f"Deleting redirect '{code}' is not implemented yet.")
