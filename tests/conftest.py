"""Shared pytest configuration: make the app package importable from src/."""

import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Settings.api_token and .default_redirect_url are required fields; give the
# whole suite stable defaults so tests that don't care about them don't need
# to set them individually.
os.environ.setdefault("API_TOKEN", "test-api-token")
os.environ.setdefault("DEFAULT_REDIRECT_URL", "https://example.com")
