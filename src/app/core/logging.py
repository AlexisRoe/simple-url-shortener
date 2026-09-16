"""Unified application logging.

Logging is entirely controlled through configuration
(:class:`app.core.config.Settings`, itself sourced from the environment):
whether logging is enabled at all, the minimum level emitted, and the
output style (plain text or JSON). All application loggers are nested
under the ``"app"`` namespace so a single call to
:func:`configure_logging` governs the whole application.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import Settings

_ROOT_LOGGER_NAME = "app"


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON-encoded, single-line representation of the record.
        """
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def configure_logging(settings: Settings) -> None:
    """Configure the application's root logger from settings.

    Safe to call multiple times (e.g. in tests): existing handlers on the
    application logger are replaced rather than stacked.

    Args:
        settings: Validated application settings controlling whether
            logging is enabled, the minimum log level, and the log style.
    """
    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    root_logger.handlers.clear()
    root_logger.propagate = False

    if not settings.log_enabled:
        root_logger.addHandler(logging.NullHandler())
        root_logger.setLevel(logging.CRITICAL + 1)
        return

    handler = logging.StreamHandler(stream=sys.stdout)

    if settings.log_style == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger nested under the application's root logger.

    Args:
        name: Suffix identifying the module/component requesting a logger,
            e.g. ``"redis"`` or ``"routes.status"``.

    Returns:
        A logger named ``"app.<name>"``.
    """

    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
