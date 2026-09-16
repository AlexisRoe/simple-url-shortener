"""Shared pytest configuration: make the app package importable from src/."""

import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Settings' scoped API tokens and .default_redirect_url are required fields;
# give the whole suite stable defaults so tests that don't care about them
# don't need to set them individually. The delete-scoped token is kept as
# "test-api-token" for backwards compatibility with tests written before
# scoping existed -- since delete outranks read/read_write in the role
# hierarchy, it satisfies every existing AUTH_HEADERS usage unchanged.
os.environ.setdefault("API_TOKEN_READ", "test-api-token-read")
os.environ.setdefault("API_TOKEN_READ_EXPIRES_AT", "2099-01-01T00:00:00Z")
os.environ.setdefault("API_TOKEN_READ_WRITE", "test-api-token-read-write")
os.environ.setdefault("API_TOKEN_READ_WRITE_EXPIRES_AT", "2099-01-01T00:00:00Z")
os.environ.setdefault("API_TOKEN_DELETE", "test-api-token")
os.environ.setdefault("API_TOKEN_DELETE_EXPIRES_AT", "2099-01-01T00:00:00Z")
os.environ.setdefault("DEFAULT_REDIRECT_URL", "https://example.com")
