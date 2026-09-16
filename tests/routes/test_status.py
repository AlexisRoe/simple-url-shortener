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


def test_livez_reports_ok_without_checking_redis():
    """GET /health/livez reports ok without depending on Redis at all."""
    with patch("app.routes.status.check_redis_connection") as mock_check:
        response = client.get("/health/livez")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    mock_check.assert_not_called()


def test_readyz_reports_ok_when_redis_connected():
    """GET /health/readyz returns 200 ok when Redis is reachable."""
    with patch("app.routes.status.check_redis_connection", return_value=True):
        response = client.get("/health/readyz")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"


def test_readyz_reports_unavailable_when_redis_unreachable():
    """GET /health/readyz returns 503 unavailable when Redis is unreachable."""
    with patch("app.routes.status.check_redis_connection", return_value=False):
        response = client.get("/health/readyz")

    body = response.json()
    assert response.status_code == 503
    assert body["status"] == "unavailable"
