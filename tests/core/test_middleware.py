"""Tests for app.core.middleware."""

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
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


def test_require_api_token_rejects_expired_token(monkeypatch):
    """A token that matches but has expired is rejected with 401 token_expired."""
    monkeypatch.setenv("API_TOKEN_READ_EXPIRES_AT", "2000-01-01T00:00:00Z")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())

        response = client.get("/api/whoami", headers={"Authorization": "Bearer test-api-token-read"})

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "token_expired"
    finally:
        monkeypatch.delenv("API_TOKEN_READ_EXPIRES_AT", raising=False)
        get_settings.cache_clear()


def test_require_api_token_rejects_read_token_on_write_request():
    """A read-scoped token is rejected with 403 when used for a write request."""
    client = TestClient(create_app())

    response = client.post(
        "/api",
        json={"url": "https://example.com"},
        headers={"Authorization": "Bearer test-api-token-read"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_scope"


def test_require_api_token_allows_read_write_token_on_write_request(monkeypatch):
    """A read_write-scoped token is accepted for a write request."""
    from unittest.mock import MagicMock

    fake_redis = MagicMock()
    fake_redis.exists.return_value = 0
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com", -1]
    fake_redis.pipeline.return_value = pipe
    monkeypatch.setattr("app.routes.api.get_redis_client", lambda: fake_redis)

    client = TestClient(create_app())

    response = client.post(
        "/api",
        json={"url": "https://example.com"},
        headers={"Authorization": "Bearer test-api-token-read-write"},
    )

    assert response.status_code == 201


def test_require_api_token_rejects_read_write_token_on_delete_request():
    """A read_write-scoped token is rejected with 403 on a delete request."""
    client = TestClient(create_app())

    response = client.delete("/api/some-code", headers={"Authorization": "Bearer test-api-token-read-write"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_scope"


def test_whoami_reports_role_and_expiry():
    """GET /api/whoami reports the authenticated token's role and remaining validity."""
    client = TestClient(create_app())

    response = client.get("/api/whoami", headers={"Authorization": "Bearer test-api-token-read"})

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "read"
    assert body["expires_in_seconds"] > 0
