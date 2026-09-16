"""Short-code generation and format validation.

A short code is a cryptographically random string, generated once at
creation time and stored as its own Redis key. There's nothing to derive
or re-verify from the code itself later on, so validation here only
checks that a candidate code is *shaped* like one of ours (correct length
and charset) before it's used to build a Redis key — cheap sanitization
of path input, not a cryptographic guarantee.
"""

from __future__ import annotations

import re
import secrets

from app.core.constants import CODE_LENGTH, VARIANT_MAX_LENGTH

_CODE_PATTERN = re.compile(rf"^[A-Za-z0-9_-]{{{CODE_LENGTH}}}$")
_VARIANT_PATTERN = re.compile(rf"^[a-zA-Z]{{1,{VARIANT_MAX_LENGTH}}}$")


def generate_short_code() -> str:
    """Generate a new cryptographically random short code.

    Returns:
        A random string of length :data:`CODE_LENGTH` drawn from the
        URL-safe base64 alphabet (``[A-Za-z0-9_-]``), via
        :func:`secrets.token_urlsafe`.
    """
    return secrets.token_urlsafe(16)[:CODE_LENGTH]


def is_valid_code_format(code: str) -> bool:
    """Check that ``code`` has the shape of a value produced by :func:`generate_short_code`.

    Args:
        code: The candidate short code, e.g. extracted from a URL path.

    Returns:
        True if ``code`` matches the expected length and charset.
    """
    return bool(_CODE_PATTERN.match(code))


def is_valid_variant_format(variant: str) -> bool:
    """Check that ``variant`` is a valid variant string.

    A valid variant is 1-10 characters long and contains only ASCII
    letters (``a-z``, ``A-Z``).

    Args:
        variant: The candidate variant string.

    Returns:
        True if ``variant`` matches the expected length and charset.
    """
    return bool(_VARIANT_PATTERN.match(variant))
