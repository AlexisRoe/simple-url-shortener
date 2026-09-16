"""Tests for the /status route."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_status_reports_ok_when_redis_connected():
    """GET /status reports status "ok" and the app identity when Redis is up."""
    with patch("app.routes.status.check_redis_connection", return_value=True):
        response = client.get("/status")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["redis_connected"] is True
    assert body["name"]
    assert body["version"]
    assert body["date"]


def test_status_reports_degraded_when_redis_unreachable():
    """GET /status reports status "degraded" when Redis is unreachable."""
    with patch("app.routes.status.check_redis_connection", return_value=False):
        response = client.get("/status")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "degraded"
    assert body["redis_connected"] is False
