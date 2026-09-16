"""Tests for the /api (redirect management) routes.

Each request includes the shared test bearer token (see tests/conftest.py)
since these routes live under /api/* and are protected by
app.core.middleware.require_api_token.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer test-api-token"}


@pytest.fixture
def fake_redis(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr("app.routes.api.get_redis_client", lambda: fake)
    return fake


def test_list_redirects_returns_empty_page_when_no_keys(fake_redis):
    fake_redis.scan_iter.return_value = iter([])

    response = client.get("/api", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_list_redirects_groups_base_and_variant_keys(fake_redis):
    fake_redis.scan_iter.return_value = iter(["sh:aB3dE5gH7j", "sh:aB3dE5gH7j:abc"])
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com/base", "https://example.com/variant", 100, 200]
    fake_redis.pipeline.return_value = pipe

    response = client.get("/api", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"] == [
        {
            "code": "aB3dE5gH7j",
            "url": "https://example.com/base",
            "ttl": 100,
            "variants": [{"variant": "abc", "url": "https://example.com/variant", "ttl": 200}],
        }
    ]


def test_list_redirects_rejects_page_size_over_max(fake_redis):
    response = client.get("/api", headers=AUTH_HEADERS, params={"page_size": 101})
    assert response.status_code == 422


def test_create_redirect_is_not_implemented():
    """POST /api reports 501 not_implemented."""
    response = client.post("/api", headers=AUTH_HEADERS, json={})
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"


def test_get_redirect_is_not_implemented():
    """GET /api/{code} reports 501 not_implemented."""
    response = client.get("/api/abc123", headers=AUTH_HEADERS)
    assert response.status_code == 501
    assert "abc123" in response.json()["error"]["message"]


def test_update_redirect_is_not_implemented():
    """PATCH /api/{code} reports 501 not_implemented."""
    response = client.patch("/api/abc123", headers=AUTH_HEADERS, json={})
    assert response.status_code == 501
    assert "abc123" in response.json()["error"]["message"]


def test_delete_redirect_is_not_implemented():
    """DELETE /api/{code} reports 501 not_implemented."""
    response = client.delete("/api/abc123", headers=AUTH_HEADERS)
    assert response.status_code == 501
    assert "abc123" in response.json()["error"]["message"]


def test_redirect_routes_require_auth():
    """Every /api route rejects requests without a bearer token."""
    assert client.get("/api").status_code == 401
    assert client.post("/api", json={}).status_code == 401
    assert client.get("/api/abc123").status_code == 401
    assert client.patch("/api/abc123", json={}).status_code == 401
    assert client.delete("/api/abc123").status_code == 401
