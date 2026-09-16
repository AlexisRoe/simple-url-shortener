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
    """OpenAPI docs are not served when APP_ENV is not development.

    Unrouted paths (including /docs when disabled) fall through to the
    catch-all 404 handler, which redirects to the default redirect URL
    instead of returning a bare 404.
    """
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get("/docs", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == get_settings().default_redirect_url
    finally:
        monkeypatch.delenv("APP_ENV", raising=False)
        get_settings.cache_clear()


def test_unknown_path_redirects_to_default_redirect_url():
    """Any request to an unregistered route redirects to the default URL."""
    client = TestClient(create_app())
    response = client.get("/this-route-does-not-exist", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == get_settings().default_redirect_url


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


def test_unhandled_exception_returns_unified_error_shape(monkeypatch):
    """Any exception not explicitly handled is rendered as a 500 in the same shape."""
    get_settings.cache_clear()
    app = create_app()

    @app.get("/__unexpected")
    def _unexpected() -> None:
        raise ValueError("something broke")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/__unexpected")

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "Internal server error."}}
