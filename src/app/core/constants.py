"""Shared constants used across the application."""

from __future__ import annotations

# Prefix for every short-link Redis key, e.g. "sh:<code>" or "sh:<code>:<variant>".
SHORT_CODE_KEY_PREFIX = "sh"

# Length, in characters, of a generated short code.
CODE_LENGTH = 10
# Maximum length, in characters, of a variant string.
VARIANT_MAX_LENGTH = 10

# Number of redirects returned per page when a request omits page_size.
DEFAULT_PAGE_SIZE = 20
# Largest page_size a request is allowed to ask for.
MAX_PAGE_SIZE = 100

# Number of collision retries allowed when generating a new short code.
MAX_CODE_GENERATION_ATTEMPTS = 5
