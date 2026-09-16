"""Tests for app.core.codes."""

from app.core.codes import generate_short_code, is_valid_code_format, is_valid_variant_format
from app.core.constants import CODE_LENGTH


def test_generate_short_code_has_expected_length():
    code = generate_short_code()
    assert len(code) == CODE_LENGTH


def test_generate_short_code_is_valid_format():
    code = generate_short_code()
    assert is_valid_code_format(code) is True


def test_generate_short_code_is_not_deterministic():
    codes = {generate_short_code() for _ in range(20)}
    assert len(codes) == 20


def test_is_valid_code_format_rejects_wrong_length():
    assert is_valid_code_format("abc") is False


def test_is_valid_code_format_rejects_disallowed_chars():
    assert is_valid_code_format("!!!!!!!!!!") is False


def test_is_valid_code_format_accepts_alphanumeric():
    assert is_valid_code_format("aB3dE5gH7j") is True


def test_is_valid_code_format_accepts_url_safe_symbols():
    assert is_valid_code_format("aB3d-5gH_j") is True


def test_is_valid_variant_format_accepts_letters_only():
    assert is_valid_variant_format("abcABC") is True


def test_is_valid_variant_format_rejects_digits():
    assert is_valid_variant_format("abc123") is False


def test_is_valid_variant_format_rejects_empty():
    assert is_valid_variant_format("") is False


def test_is_valid_variant_format_rejects_too_long():
    assert is_valid_variant_format("a" * 11) is False


def test_is_valid_variant_format_accepts_max_length():
    assert is_valid_variant_format("a" * 10) is True
