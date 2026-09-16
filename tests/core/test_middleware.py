"""Tests for app.core.middleware."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import configure_logging
from app.main import create_app


def test_log_requests_logs_method_path_and_status(capsys):
    """Every request is logged with its method, path, and response status."""
    configure_logging(Settings(_env_file=None, LOG_ENABLED=True, LOG_LEVEL="INFO", LOG_STYLE="text"))
    client = TestClient(create_app())

    response = client.get("/ping")

    captured = capsys.readouterr()
    assert response.status_code == 200
    assert "GET /ping -> 200" in captured.out


def test_require_api_token_blocks_unauthenticated_api_request():
    """A request to /api/* without a bearer token is rejected with 401."""
    client = TestClient(create_app())

    response = client.get("/api")

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "unauthorized", "message": "Missing or invalid bearer token."}
    }


def test_require_api_token_blocks_wrong_token():
    """A request to /api/* with an incorrect bearer token is rejected with 401."""
    client = TestClient(create_app())

    response = client.get("/api", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401


def test_require_api_token_allows_correct_token(monkeypatch):
    """A request to /api/* with the correct bearer token passes through to the route."""
    from unittest.mock import MagicMock

    fake_redis = MagicMock()
    fake_redis.scan_iter.return_value = iter([])
    monkeypatch.setattr("app.routes.api.get_redis_client", lambda: fake_redis)

    client = TestClient(create_app())

    response = client.get("/api/some-code", headers={"Authorization": "Bearer test-api-token"})

    # Reaches the route handler (past auth), which reports 404 since the code doesn't exist.
    assert response.status_code == 404


def test_require_api_token_does_not_affect_non_api_routes():
    """Routes outside /api/* are unaffected by the bearer-token check."""
    client = TestClient(create_app())

    response = client.get("/ping")

    assert response.status_code == 200
