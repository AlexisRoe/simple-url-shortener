"""Tests for the /sh/{code} stub route."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_resolve_short_code_is_not_implemented():
    """GET /sh/{code} reports 501 not_implemented (stub) without needing auth."""
    response = client.get("/sh/abc123")

    assert response.status_code == 501
    body = response.json()
    assert body["error"]["code"] == "not_implemented"
    assert "abc123" in body["error"]["message"]
