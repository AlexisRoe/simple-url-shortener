"""Request body shapes for the redirect management routes.

Field types here are deliberately loose (``str``/``int``); all
business-rule validation (URL format, TTL positivity, variant charset,
existence checks) happens in the use-cases and raises :class:`~app.core.errors.AppError`
subclasses, keeping every validation failure in this API on the same
unified error shape rather than mixing in pydantic's own 422 responses.
"""

from __future__ import annotations

from pydantic import BaseModel


class CreateRedirectBody(BaseModel):
    """Body for ``POST /api``."""

    url: str
    ttl: int | None = None


class CreateVariantBody(BaseModel):
    """Body for ``POST /api/{code}/variants``."""

    url: str
    ttl: int | None = None
    variant: str


class UpdateRedirectBody(BaseModel):
    """Body for ``PATCH /api/{code}``.

    When ``variant`` is omitted, the base code's entry is updated;
    otherwise the specific ``code``+``variant`` entry is updated.
    """

    url: str
    ttl: int | None = None
    variant: str | None = None
