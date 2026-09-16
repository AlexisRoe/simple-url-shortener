"""Tests for app.core.security."""

from app.core.security import extract_bearer_token, is_valid_api_token


def test_extract_bearer_token_returns_token():
    """A well-formed Bearer header yields the token."""
    assert extract_bearer_token("Bearer abc123") == "abc123"


def test_extract_bearer_token_is_case_insensitive_on_scheme():
    """The "Bearer" scheme is matched case-insensitively."""
    assert extract_bearer_token("bearer abc123") == "abc123"


def test_extract_bearer_token_returns_none_when_missing():
    """A missing header returns None."""
    assert extract_bearer_token(None) is None


def test_extract_bearer_token_returns_none_for_wrong_scheme():
    """A non-Bearer scheme (e.g. Basic) returns None."""
    assert extract_bearer_token("Basic abc123") is None


def test_extract_bearer_token_returns_none_for_malformed_header():
    """A header with no token portion returns None."""
    assert extract_bearer_token("Bearer") is None


def test_is_valid_api_token_true_on_match():
    """A token equal to the expected token is valid."""
    assert is_valid_api_token("secret", "secret") is True


def test_is_valid_api_token_false_on_mismatch():
    """A token that differs from the expected token is invalid."""
    assert is_valid_api_token("wrong", "secret") is False


def test_is_valid_api_token_false_when_none():
    """A missing token is invalid."""
    assert is_valid_api_token(None, "secret") is False
