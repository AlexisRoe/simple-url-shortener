"""Tests for the list_redirects use-case."""

from unittest.mock import MagicMock

from app.use_cases.list_redirects import list_redirects


def _fake_redis(keys, values, ttls):
    client = MagicMock()
    client.scan_iter.side_effect = lambda **kwargs: iter(keys)
    pipe = MagicMock()
    pipe.execute.return_value = [*values, *ttls]
    client.pipeline.return_value = pipe
    return client


def test_list_redirects_returns_empty_page_when_no_keys():
    client = _fake_redis([], [], [])

    result = list_redirects(redis_client=client, page=1, page_size=20)

    assert result.items == []
    assert result.total == 0


def test_list_redirects_groups_variants_under_their_base_code():
    keys = ["sh:aB3dE5gH7j", "sh:aB3dE5gH7j:abc", "sh:aB3dE5gH7j:xyz"]
    values = ["https://example.com/base", "https://example.com/a", "https://example.com/x"]
    ttls = [100, 200, 300]
    client = _fake_redis(keys, values, ttls)

    result = list_redirects(redis_client=client, page=1, page_size=20)

    assert result.total == 1
    redirect = result.items[0]
    assert redirect.code == "aB3dE5gH7j"
    assert redirect.url == "https://example.com/base"
    assert redirect.ttl == 100
    assert {v.variant for v in redirect.variants} == {"abc", "xyz"}


def test_list_redirects_skips_expired_keys_with_none_value():
    keys = ["sh:aB3dE5gH7j"]
    values = [None]
    ttls = [-2]
    client = _fake_redis(keys, values, ttls)

    result = list_redirects(redis_client=client, page=1, page_size=20)

    assert result.total == 0


def test_list_redirects_paginates_sorted_codes():
    keys = ["sh:bbbbbbbbbb", "sh:aaaaaaaaaa", "sh:ccccccccc0"]
    values = ["https://b", "https://a", "https://c"]
    ttls = [-1, -1, -1]
    client = _fake_redis(keys, values, ttls)

    result = list_redirects(redis_client=client, page=1, page_size=2)

    assert result.total == 3
    assert [r.code for r in result.items] == ["aaaaaaaaaa", "bbbbbbbbbb"]

    result_page_2 = list_redirects(redis_client=client, page=2, page_size=2)
    assert [r.code for r in result_page_2.items] == ["ccccccccc0"]
