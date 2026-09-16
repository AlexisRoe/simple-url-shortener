"""Tests for the FastAPI application factory."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_docs_available_in_development(monkeypatch):
    """OpenAPI docs are served at /docs when APP_ENV=development."""
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get("/docs")
        assert response.status_code == 200
    finally:
        monkeypatch.delenv("APP_ENV", raising=False)
        get_settings.cache_clear()


def test_docs_disabled_outside_development(monkeypatch):
    """OpenAPI docs are not served when APP_ENV is not development."""
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get("/docs")
        assert response.status_code == 404
    finally:
        monkeypatch.delenv("APP_ENV", raising=False)
        get_settings.cache_clear()


def test_app_error_handler_returns_unified_error_shape(monkeypatch):
    """AppError subclasses are rendered as a unified {code, message} JSON error."""
    get_settings.cache_clear()
    app = create_app()

    @app.get("/__boom")
    def _boom() -> None:
        from app.core.errors import RedisConnectionError

        raise RedisConnectionError("nope")

    client = TestClient(app)
    response = client.get("/__boom")

    assert response.status_code == 503
    assert response.json() == {"error": {"code": "redis_connection_error", "message": "nope"}}
