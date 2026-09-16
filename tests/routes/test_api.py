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


def test_create_redirect_returns_201_and_created_entry(fake_redis):
    fake_redis.exists.return_value = 0
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com", -1]
    fake_redis.pipeline.return_value = pipe

    response = client.post("/api", headers=AUTH_HEADERS, json={"url": "https://example.com"})

    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://example.com"
    assert body["ttl"] == -1
    assert body["variants"] == []
    fake_redis.set.assert_called_once()


def test_create_redirect_rejects_invalid_url(fake_redis):
    response = client.post("/api", headers=AUTH_HEADERS, json={"url": "not-a-url"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_url"


def test_create_redirect_rejects_http_url(fake_redis):
    response = client.post("/api", headers=AUTH_HEADERS, json={"url": "http://example.com"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "insecure_url"


def test_create_redirect_rejects_non_positive_ttl(fake_redis):
    response = client.post("/api", headers=AUTH_HEADERS, json={"url": "https://example.com", "ttl": 0})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_ttl"


def test_create_variant_returns_201(fake_redis):
    fake_redis.exists.return_value = 1
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com/v", 500]
    fake_redis.pipeline.return_value = pipe

    response = client.post(
        "/api/aB3dE5gH7j/variants",
        headers=AUTH_HEADERS,
        json={"url": "https://example.com/v", "variant": "ab", "ttl": 500},
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {"code": "aB3dE5gH7j", "variant": "ab", "url": "https://example.com/v", "ttl": 500}


def test_create_variant_404_when_code_missing(fake_redis):
    fake_redis.exists.return_value = 0

    response = client.post(
        "/api/aB3dE5gH7j/variants",
        headers=AUTH_HEADERS,
        json={"url": "https://example.com/v", "variant": "ab"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "redirect_not_found"


def test_get_redirect_returns_entry(fake_redis):
    fake_redis.scan_iter.return_value = iter(["sh:aB3dE5gH7j"])
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com", 100]
    fake_redis.pipeline.return_value = pipe

    response = client.get("/api/aB3dE5gH7j", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "code": "aB3dE5gH7j",
        "url": "https://example.com",
        "ttl": 100,
        "variants": [],
    }


def test_get_redirect_404_when_missing(fake_redis):
    fake_redis.scan_iter.return_value = iter([])

    response = client.get("/api/aB3dE5gH7j", headers=AUTH_HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "redirect_not_found"


def test_update_redirect_returns_updated_entry(fake_redis):
    fake_redis.exists.return_value = 1
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com/new", -1]
    fake_redis.pipeline.return_value = pipe

    response = client.patch("/api/aB3dE5gH7j", headers=AUTH_HEADERS, json={"url": "https://example.com/new"})

    assert response.status_code == 200
    assert response.json() == {
        "code": "aB3dE5gH7j",
        "variant": None,
        "url": "https://example.com/new",
        "ttl": -1,
    }


def test_update_redirect_404_when_missing(fake_redis):
    fake_redis.exists.return_value = 0

    response = client.patch("/api/aB3dE5gH7j", headers=AUTH_HEADERS, json={"url": "https://example.com/new"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "redirect_not_found"


def test_delete_redirect_returns_204(fake_redis):
    fake_redis.exists.return_value = 1

    response = client.delete("/api/aB3dE5gH7j", headers=AUTH_HEADERS)

    assert response.status_code == 204
    fake_redis.delete.assert_called_once_with("sh:aB3dE5gH7j")


def test_delete_redirect_with_variant(fake_redis):
    fake_redis.exists.return_value = 1

    response = client.delete("/api/aB3dE5gH7j", headers=AUTH_HEADERS, params={"variant": "ab"})

    assert response.status_code == 204
    fake_redis.delete.assert_called_once_with("sh:aB3dE5gH7j:ab")


def test_delete_redirect_404_when_missing(fake_redis):
    fake_redis.exists.return_value = 0

    response = client.delete("/api/aB3dE5gH7j", headers=AUTH_HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "redirect_not_found"


def test_delete_all_redirects_returns_204(fake_redis):
    fake_redis.exists.return_value = 1
    fake_redis.scan_iter.return_value = iter(["sh:aB3dE5gH7j", "sh:aB3dE5gH7j:ab"])

    response = client.delete("/api/aB3dE5gH7j/all", headers=AUTH_HEADERS)

    assert response.status_code == 204
    fake_redis.delete.assert_called_once_with("sh:aB3dE5gH7j", "sh:aB3dE5gH7j:ab")


def test_delete_all_redirects_404_when_missing(fake_redis):
    fake_redis.exists.return_value = 0

    response = client.delete("/api/aB3dE5gH7j/all", headers=AUTH_HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "redirect_not_found"


def test_redirect_routes_require_auth():
    """Every /api route rejects requests without a bearer token."""
    assert client.get("/api").status_code == 401
    assert client.post("/api", json={}).status_code == 401
    assert client.post("/api/abc123/variants", json={}).status_code == 401
    assert client.get("/api/abc123").status_code == 401
    assert client.patch("/api/abc123", json={}).status_code == 401
    assert client.delete("/api/abc123").status_code == 401
    assert client.delete("/api/abc123/all").status_code == 401
