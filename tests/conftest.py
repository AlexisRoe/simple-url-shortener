"""Shared pytest configuration: make the app package importable from src/."""

import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Settings.api_token is a required field; give the whole suite a stable
# default so tests that don't care about auth don't need to set it themselves.
os.environ.setdefault("API_TOKEN", "test-api-token")
