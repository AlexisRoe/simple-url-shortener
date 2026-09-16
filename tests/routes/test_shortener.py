"""Tests for the /sh/{code} route."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app, follow_redirects=False)

VALID_CODE = "aB3dE5gH7j"


@pytest.fixture
def fake_redis(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr("app.routes.shortener.get_redis_client", lambda: fake)
    return fake


def test_resolve_short_code_rejects_invalid_code_format():
    response = client.get("/sh/not-a-real-code")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "invalid_short_code"


def test_resolve_short_code_rejects_invalid_variant_format():
    response = client.get(f"/sh/{VALID_CODE}", params={"variant": "123"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_variant"


def test_resolve_short_code_redirects_to_base_url(fake_redis):
    fake_redis.get.return_value = "https://example.com/target"

    response = client.get(f"/sh/{VALID_CODE}")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/target"


def test_resolve_short_code_prefers_variant_url(fake_redis):
    fake_redis.mget.return_value = ["https://example.com/variant-a", "https://example.com/base"]

    response = client.get(f"/sh/{VALID_CODE}", params={"variant": "abc"})

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/variant-a"
    fake_redis.mget.assert_called_once_with(f"sh:{VALID_CODE}:abc", f"sh:{VALID_CODE}")


def test_resolve_short_code_falls_back_to_default_url(fake_redis):
    fake_redis.get.return_value = None

    response = client.get(f"/sh/{VALID_CODE}")

    assert response.status_code == 302
    assert response.headers["location"] == get_settings().default_redirect_url
