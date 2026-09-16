"""Response shape for ``GET /api/whoami``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WhoAmI(BaseModel):
    """Describes the bearer token that authenticated the current request."""

    role: str
    expires_at: datetime
    expires_in_seconds: int
