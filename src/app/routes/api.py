"""Redirect management routes (``/api``).

Covers full CRUD for a single redirect plus an overview listing of all
existing redirects. All routes here live under ``/api`` and are therefore
protected by the bearer-token auth middleware
(:func:`app.core.middleware.require_api_token`).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request, Response

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.redirect import CreateRedirectBody, CreateVariantBody, UpdateRedirectBody
from app.schemas.token import WhoAmI
from app.services.redis_client import get_redis_client
from app.use_cases.create_redirect import create_redirect as create_redirect_use_case
from app.use_cases.create_variant import CreatedVariant
from app.use_cases.create_variant import create_variant as create_variant_use_case
from app.use_cases.delete_all_redirects import delete_all_redirects as delete_all_redirects_use_case
from app.use_cases.delete_redirect import delete_redirect as delete_redirect_use_case
from app.use_cases.get_redirect import get_redirect as get_redirect_use_case
from app.use_cases.list_redirects import Redirect, RedirectPage
from app.use_cases.list_redirects import list_redirects as list_redirects_use_case
from app.use_cases.update_redirect import UpdatedRedirect
from app.use_cases.update_redirect import update_redirect as update_redirect_use_case

router = APIRouter(prefix="/api", tags=["redirect"])


@router.get("", summary="List all redirects")
def list_redirects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> RedirectPage:
    """Return a paginated overview of all existing redirects.

    Args:
        page: The 1-indexed page number to return.
        page_size: The maximum number of redirects per page (max 100).

    Returns:
        The requested page of redirects, plus pagination metadata.
    """
    return list_redirects_use_case(redis_client=get_redis_client(), page=page, page_size=page_size)


@router.get("/whoami", summary="Describe the authenticated token")
def whoami(request: Request) -> WhoAmI:
    """Report the role and remaining validity of the request's bearer token.

    Lets a client check, ahead of time, whether its token is close to
    expiring and needs to be refreshed, rather than finding out via a
    sudden 401.

    Returns:
        The token's role (read / read_write / delete), its expiry
        timestamp, and the number of seconds remaining until then.
    """
    role = request.state.token_role
    expires_at = request.state.token_expires_at
    remaining = (expires_at - datetime.now(UTC)).total_seconds()

    return WhoAmI(
        role=role.name.lower(),
        expires_at=expires_at,
        expires_in_seconds=max(0, int(remaining)),
    )


@router.post("", summary="Create a redirect", status_code=201)
def create_redirect(body: CreateRedirectBody) -> Redirect:
    """Create a new shortened-URL redirect.

    Args:
        body: The target URL and optional TTL (milliseconds).

    Returns:
        The newly created redirect.

    Raises:
        InvalidUrlError: If the URL isn't a valid absolute http(s) URL.
        InvalidTtlError: If the TTL is supplied but isn't a positive integer.
    """
    return create_redirect_use_case(redis_client=get_redis_client(), url=body.url, ttl=body.ttl)


@router.post("/{code}/variants", summary="Create a variant for an existing redirect", status_code=201)
def create_variant(code: str, body: CreateVariantBody) -> CreatedVariant:
    """Create a variant URL under an existing short code.

    Args:
        code: The short code the variant belongs to. Must already exist.
        body: The variant string, target URL, and optional TTL (milliseconds).

    Returns:
        The newly created variant.

    Raises:
        RedirectNotFoundError: If ``code`` doesn't exist.
        InvalidVariantError: If the variant fails format validation.
        InvalidUrlError: If the URL isn't a valid absolute http(s) URL.
        InvalidTtlError: If the TTL is supplied but isn't a positive integer.
    """
    return create_variant_use_case(
        redis_client=get_redis_client(), code=code, variant=body.variant, url=body.url, ttl=body.ttl
    )


@router.get("/{code}", summary="Get a single redirect")
def get_redirect(code: str) -> Redirect:
    """Fetch a single redirect by its short code.

    Args:
        code: The short code identifying the redirect.

    Returns:
        The redirect, with its base URL, TTL, and any variants.

    Raises:
        RedirectNotFoundError: If ``code`` doesn't exist.
    """
    return get_redirect_use_case(redis_client=get_redis_client(), code=code)


@router.patch("/{code}", summary="Update a single redirect")
def update_redirect(code: str, body: UpdateRedirectBody) -> UpdatedRedirect:
    """Update a single redirect entry: a code, or a code+variant.

    Args:
        code: The short code identifying the redirect.
        body: The new URL and optional TTL (milliseconds), plus an
            optional variant selecting which entry under ``code`` to
            update. When omitted, the base code's entry is updated.

    Returns:
        The updated entry.

    Raises:
        InvalidVariantError: If a variant is supplied but fails format
            validation.
        InvalidUrlError: If the URL isn't a valid absolute http(s) URL.
        InvalidTtlError: If the TTL is supplied but isn't a positive integer.
        RedirectNotFoundError: If the targeted entry doesn't exist.
    """
    return update_redirect_use_case(
        redis_client=get_redis_client(), code=code, variant=body.variant, url=body.url, ttl=body.ttl
    )


@router.delete("/{code}", summary="Delete a single redirect", status_code=204)
def delete_redirect(code: str, variant: str | None = None) -> Response:
    """Delete a single redirect entry: a code, or a code+variant.

    Args:
        code: The short code identifying the redirect.
        variant: The optional variant identifying a specific entry under
            ``code``. When omitted, the base code's entry is deleted.

    Raises:
        RedirectNotFoundError: If the targeted entry doesn't exist.
    """
    delete_redirect_use_case(redis_client=get_redis_client(), code=code, variant=variant)
    return Response(status_code=204)


@router.delete("/{code}/all", summary="Delete a redirect and all of its variants", status_code=204)
def delete_all_redirects(code: str) -> Response:
    """Delete a short code's base entry and all of its variant entries at once.

    Args:
        code: The short code identifying the redirect.

    Raises:
        RedirectNotFoundError: If ``code`` doesn't exist.
    """
    delete_all_redirects_use_case(redis_client=get_redis_client(), code=code)
    return Response(status_code=204)
