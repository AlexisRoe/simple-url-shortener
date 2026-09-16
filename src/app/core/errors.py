"""Unified application error hierarchy.

Every error raised deliberately by application code inherits from
:class:`AppError`, giving the whole codebase (and the API's error
responses) a single, predictable shape: a human-readable message, an
HTTP status code, and a short machine-readable code.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application-raised errors.

    Args:
        message: Human-readable description of what went wrong.
        status_code: HTTP status code to use when this error is turned
            into an API response.
        code: Short, machine-readable identifier for the error type,
            stable across releases (used by API clients).
    """

    def __init__(self, message: str, *, status_code: int = 500, code: str = "app_error") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class ConfigurationError(AppError):
    """Raised when required configuration is missing or fails validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500, code="configuration_error")


class RedisConnectionError(AppError):
    """Raised when the connection to the Redis/Valkey server fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503, code="redis_connection_error")


class UnauthorizedError(AppError):
    """Raised when a request to a protected endpoint lacks valid credentials."""

    def __init__(self, message: str = "Missing or invalid bearer token.") -> None:
        super().__init__(message, status_code=401, code="unauthorized")


class TokenExpiredError(AppError):
    """Raised when a bearer token matches a configured token but has expired."""

    def __init__(self, message: str = "This API token has expired.") -> None:
        super().__init__(message, status_code=401, code="token_expired")


class InsufficientScopeError(AppError):
    """Raised when a valid, unexpired token's role doesn't cover the request."""

    def __init__(self, message: str = "This token's scope does not permit this action.") -> None:
        super().__init__(message, status_code=403, code="insufficient_scope")


class InvalidShortCodeError(AppError):
    """Raised when a short code's format doesn't match a generated code."""

    def __init__(self, message: str = "Invalid short code.") -> None:
        super().__init__(message, status_code=404, code="invalid_short_code")


class InvalidVariantError(AppError):
    """Raised when a variant query parameter fails format validation."""

    def __init__(self, message: str = "Invalid variant.") -> None:
        super().__init__(message, status_code=400, code="invalid_variant")


class FeatureNotImplementedError(AppError):
    """Raised by stub endpoints whose logic has not been implemented yet."""

    def __init__(self, message: str = "This endpoint is not implemented yet.") -> None:
        super().__init__(message, status_code=501, code="not_implemented")


class InvalidUrlError(AppError):
    """Raised when a submitted redirect target URL fails format validation."""

    def __init__(self, message: str = "Invalid URL.") -> None:
        super().__init__(message, status_code=400, code="invalid_url")


class InsecureUrlError(AppError):
    """Raised when a submitted redirect target URL uses plain http instead of https."""

    def __init__(self, message: str = "Only https URLs are allowed.") -> None:
        super().__init__(message, status_code=400, code="insecure_url")


class DomainNotAllowedError(AppError):
    """Raised when a submitted redirect target URL's host isn't on the allowlist."""

    def __init__(self, message: str = "This domain is not on the allowlist.") -> None:
        super().__init__(message, status_code=400, code="domain_not_allowed")


class InvalidTtlError(AppError):
    """Raised when a submitted TTL (milliseconds) isn't a positive integer."""

    def __init__(self, message: str = "Invalid TTL.") -> None:
        super().__init__(message, status_code=400, code="invalid_ttl")


class RedirectNotFoundError(AppError):
    """Raised when a requested redirect (code or code+variant) doesn't exist."""

    def __init__(self, message: str = "Redirect not found.") -> None:
        super().__init__(message, status_code=404, code="redirect_not_found")
