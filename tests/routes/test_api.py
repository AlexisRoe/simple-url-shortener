"""Tests for the /api (redirect management) stub routes.

Each request includes the shared test bearer token (see tests/conftest.py)
since these routes live under /api/* and are protected by
app.core.middleware.require_api_token.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer test-api-token"}


def test_list_redirects_is_not_implemented():
    """GET /api (overview) reports 501 not_implemented."""
    response = client.get("/api", headers=AUTH_HEADERS)
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"


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
