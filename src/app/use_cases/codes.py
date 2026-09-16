"""Use-case helper: generate a short code guaranteed not to collide."""

from __future__ import annotations

import redis

from app.core.codes import generate_short_code
from app.core.constants import MAX_CODE_GENERATION_ATTEMPTS
from app.core.errors import AppError
from app.services.redis_client import build_short_link_key, key_exists


def generate_unique_code(redis_client: redis.Redis) -> str:
    """Generate a short code that isn't already in use.

    Args:
        redis_client: Client used to check for collisions.

    Returns:
        A short code with no existing base key in Redis.

    Raises:
        AppError: If no free code was found within a handful of attempts
            (practically unreachable given the code's keyspace size).
    """
    for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
        code = generate_short_code()

        if not key_exists(redis_client, build_short_link_key(code)):
            return code

    raise AppError("Could not generate a unique short code.", status_code=500, code="code_generation_failed")
