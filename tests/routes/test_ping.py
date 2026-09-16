"""Tests for the /ping route."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ping_returns_pong():
    """GET /ping responds 200 with the literal string "pong"."""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == "pong"
