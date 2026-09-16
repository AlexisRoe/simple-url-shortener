"""Tests for app.core.urls."""

from app.core.urls import is_allowed_domain, is_insecure_http_url, is_valid_ttl_ms, is_valid_url


def test_is_valid_url_accepts_https_only():
    assert is_valid_url("https://example.com")
    assert not is_valid_url("http://example.com")


def test_is_valid_url_accepts_query_parameters():
    assert is_valid_url("https://example.com/path?a=1&b=2")


def test_is_valid_url_rejects_missing_scheme_or_host():
    assert not is_valid_url("example.com")
    assert not is_valid_url("not-a-url")
    assert not is_valid_url("ftp://example.com")
    assert not is_valid_url("")


def test_is_insecure_http_url_detects_http_only():
    assert is_insecure_http_url("http://example.com")
    assert not is_insecure_http_url("https://example.com")
    assert not is_insecure_http_url("ftp://example.com")
    assert not is_insecure_http_url("not-a-url")


def test_is_valid_ttl_ms_accepts_none_and_positive_int():
    assert is_valid_ttl_ms(None)
    assert is_valid_ttl_ms(1)
    assert is_valid_ttl_ms(1000)


def test_is_valid_ttl_ms_rejects_zero_and_negative():
    assert not is_valid_ttl_ms(0)
    assert not is_valid_ttl_ms(-1)


def test_is_allowed_domain_allows_any_host_when_allowlist_empty():
    assert is_allowed_domain("https://anything.example", [])


def test_is_allowed_domain_accepts_exact_match():
    assert is_allowed_domain("https://company.com/path", ["company.com"])


def test_is_allowed_domain_accepts_subdomain():
    assert is_allowed_domain("https://docs.company.com", ["company.com"])


def test_is_allowed_domain_rejects_unlisted_host():
    assert not is_allowed_domain("https://evil.com", ["company.com"])


def test_is_allowed_domain_rejects_lookalike_suffix():
    assert not is_allowed_domain("https://notcompany.com", ["company.com"])


def test_is_valid_ttl_ms_rejects_non_integer_types():
    assert not is_valid_ttl_ms(500.0)
    assert not is_valid_ttl_ms(500.5)
    assert not is_valid_ttl_ms("500")
