"""Tests for the list_redirects use-case."""

from unittest.mock import MagicMock

from app.use_cases.list_redirects import list_redirects


def _fake_redis(page_codes, keys_by_code, values, ttls):
    """Build a mock redis client wired for the index-based listing flow.

    Args:
        page_codes: Codes returned by ZRANGEBYSCORE for the requested page.
        keys_by_code: Mapping of code -> keys returned by scan_iter for
            that code (base key plus any variant keys).
        values: All values returned by the pipeline GETs, in key order
            across the concatenated per-code key lists.
        ttls: All TTLs returned by the pipeline, parallel to ``values``.
    """
    client = MagicMock()
    client.zremrangebyscore.return_value = 0
    client.zcount.return_value = len(page_codes)
    client.zrangebyscore.return_value = page_codes

    def _scan_iter(match):
        code = match.rsplit(":", 1)[-1].rstrip("*")
        return iter(keys_by_code.get(code, []))

    client.scan_iter.side_effect = _scan_iter
    pipe = MagicMock()
    pipe.execute.return_value = [*values, *ttls]
    client.pipeline.return_value = pipe
    return client


def test_list_redirects_returns_empty_page_when_no_codes():
    client = _fake_redis([], {}, [], [])

    result = list_redirects(redis_client=client, page=1, page_size=20)

    assert result.items == []
    assert result.total == 0


def test_list_redirects_groups_variants_under_their_base_code():
    code = "aB3dE5gH7j"
    keys = [f"sh:{code}", f"sh:{code}:abc", f"sh:{code}:xyz"]
    values = ["https://example.com/base", "https://example.com/a", "https://example.com/x"]
    ttls = [100, 200, 300]
    client = _fake_redis([code], {code: keys}, values, ttls)

    result = list_redirects(redis_client=client, page=1, page_size=20)

    assert result.total == 1
    redirect = result.items[0]
    assert redirect.code == code
    assert redirect.url == "https://example.com/base"
    assert redirect.ttl == 100
    assert {v.variant for v in redirect.variants} == {"abc", "xyz"}


def test_list_redirects_skips_code_when_base_key_expired():
    code = "aB3dE5gH7j"
    client = _fake_redis([code], {code: [f"sh:{code}"]}, [None], [-2])

    result = list_redirects(redis_client=client, page=1, page_size=20)

    assert result.items == []


def test_list_redirects_uses_index_page_for_pagination():
    client = _fake_redis(
        ["aaaaaaaaaa", "bbbbbbbbbb"],
        {"aaaaaaaaaa": ["sh:aaaaaaaaaa"], "bbbbbbbbbb": ["sh:bbbbbbbbbb"]},
        ["https://a", "https://b"],
        [-1, -1],
    )

    result = list_redirects(redis_client=client, page=1, page_size=2)

    assert [r.code for r in result.items] == ["aaaaaaaaaa", "bbbbbbbbbb"]
    client.zrangebyscore.assert_called_once()
    _, kwargs = client.zrangebyscore.call_args
    assert kwargs["start"] == 0
    assert kwargs["num"] == 2


def test_list_redirects_purges_expired_index_entries_before_reading():
    client = _fake_redis([], {}, [], [])

    list_redirects(redis_client=client, page=1, page_size=20)

    client.zremrangebyscore.assert_called_once()
