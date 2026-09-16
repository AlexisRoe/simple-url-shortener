"""Tests for app.core.logging."""

import json
import logging

from app.core.config import Settings
from app.core.logging import configure_logging, get_logger


def test_get_logger_is_namespaced():
    """get_logger nests loggers under the shared "app" namespace."""
    logger = get_logger("widgets")
    assert logger.name == "app.widgets"


def test_configure_logging_disabled_silences_output(capsys):
    """When logging is disabled, nothing is written to stdout."""
    configure_logging(Settings(_env_file=None, LOG_ENABLED=False))
    get_logger("test-disabled").critical("should not appear")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_configure_logging_respects_minimum_level(capsys):
    """Messages below the configured minimum level are not emitted."""
    configure_logging(Settings(_env_file=None, LOG_ENABLED=True, LOG_LEVEL="WARNING", LOG_STYLE="text"))
    logger = get_logger("test-level")
    logger.info("hidden")
    logger.warning("visible")
    captured = capsys.readouterr()
    assert "hidden" not in captured.out
    assert "visible" in captured.out


def test_configure_logging_json_style_emits_valid_json(capsys):
    """The JSON log style produces a parseable single-line JSON record."""
    configure_logging(Settings(_env_file=None, LOG_ENABLED=True, LOG_LEVEL="INFO", LOG_STYLE="json"))
    get_logger("test-json").info("hello")
    captured = capsys.readouterr()
    record = json.loads(captured.out.strip())
    assert record["message"] == "hello"
    assert record["level"] == "INFO"
    assert record["logger"] == "app.test-json"


def test_configure_logging_text_style_includes_level_and_message(capsys):
    """The text log style includes the level name and message."""
    configure_logging(Settings(_env_file=None, LOG_ENABLED=True, LOG_LEVEL="INFO", LOG_STYLE="text"))
    get_logger("test-text").info("hello there")
    captured = capsys.readouterr()
    assert "[INFO]" in captured.out
    assert "hello there" in captured.out


def test_configure_logging_replaces_previous_handlers():
    """Re-configuring logging does not stack handlers across calls."""
    settings = Settings(_env_file=None, LOG_ENABLED=True, LOG_LEVEL="INFO", LOG_STYLE="text")
    configure_logging(settings)
    configure_logging(settings)
    assert len(logging.getLogger("app").handlers) == 1
