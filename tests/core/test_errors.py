"""Tests for app.core.errors."""

from app.core.errors import AppError, ConfigurationError, RedisConnectionError


def test_app_error_defaults():
    """AppError defaults to a 500 status and the generic error code."""
    err = AppError("boom")
    assert err.message == "boom"
    assert err.status_code == 500
    assert err.code == "app_error"
    assert str(err) == "boom"


def test_app_error_custom_status_and_code():
    """AppError accepts a custom status code and error code."""
    err = AppError("nope", status_code=418, code="teapot")
    assert err.status_code == 418
    assert err.code == "teapot"


def test_configuration_error_shape():
    """ConfigurationError reports its dedicated code and a 500 status."""
    err = ConfigurationError("bad config")
    assert isinstance(err, AppError)
    assert err.code == "configuration_error"
    assert err.status_code == 500
    assert err.message == "bad config"


def test_redis_connection_error_shape():
    """RedisConnectionError reports its dedicated code and a 503 status."""
    err = RedisConnectionError("unreachable")
    assert isinstance(err, AppError)
    assert err.code == "redis_connection_error"
    assert err.status_code == 503
