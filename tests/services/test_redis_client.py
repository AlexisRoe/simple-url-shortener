"""Tests for app.services.redis_client."""

import time
from unittest.mock import MagicMock

import redis

from app.core.config import Settings
from app.core.constants import SHORT_CODE_INDEX_KEY
from app.services.redis_client import (
    add_code_to_index,
    build_redis_client,
    build_short_link_key,
    check_redis_connection,
    delete_key,
    delete_keys,
    get_index_count,
    get_index_page,
    get_key_values_and_ttls,
    get_short_link_urls,
    key_exists,
    purge_expired_index_entries,
    remove_code_from_index,
    scan_keys_for_code,
    scan_short_link_keys,
    set_short_link,
)


def test_build_redis_client_uses_settings_host_and_port():
    """The client is built using the host/port from the given settings."""
    settings = Settings(_env_file=None, VALKEY_HOST="example-host", VALKEY_PORT=1234)
    client = build_redis_client(settings)
    pool_kwargs = client.connection_pool.connection_kwargs
    assert pool_kwargs["host"] == "example-host"
    assert pool_kwargs["port"] == 1234


def test_build_redis_client_uses_settings_credentials():
    """The client authenticates using the ACL username/password from settings."""
    settings = Settings(_env_file=None, VALKEY_USERNAME="alice", VALKEY_PASSWORD="s3cret")
    client = build_redis_client(settings)
    pool_kwargs = client.connection_pool.connection_kwargs
    assert pool_kwargs["username"] == "alice"
    assert pool_kwargs["password"] == "s3cret"


def test_check_redis_connection_true_on_successful_ping():
    """check_redis_connection returns True when the client's PING succeeds."""
    client = MagicMock()
    client.ping.return_value = True
    assert check_redis_connection(client) is True


def test_check_redis_connection_false_on_redis_error():
    """check_redis_connection returns False when the client raises a RedisError."""
    client = MagicMock()
    client.ping.side_effect = redis.RedisError("connection refused")
    assert check_redis_connection(client) is False


def test_get_short_link_urls_uses_get_when_no_variant():
    """Without a variant, only the base key is looked up via GET."""
    client = MagicMock()
    client.get.return_value = "https://example.com/base"

    variant_url, base_url = get_short_link_urls(client, "abc0000000", None)

    assert variant_url is None
    assert base_url == "https://example.com/base"
    client.get.assert_called_once_with("sh:abc0000000")


def test_get_short_link_urls_uses_mget_when_variant_given():
    """With a variant, both keys are looked up via MGET in one round trip."""
    client = MagicMock()
    client.mget.return_value = ["https://example.com/variant", "https://example.com/base"]

    variant_url, base_url = get_short_link_urls(client, "abc0000000", "ab")

    assert variant_url == "https://example.com/variant"
    assert base_url == "https://example.com/base"
    client.mget.assert_called_once_with("sh:abc0000000:ab", "sh:abc0000000")


def test_scan_short_link_keys_matches_prefix():
    """scan_short_link_keys queries with the sh:* prefix via SCAN."""
    client = MagicMock()
    client.scan_iter.return_value = iter(["sh:abc0000000", "sh:abc0000000:ab"])

    keys = scan_short_link_keys(client)

    assert keys == ["sh:abc0000000", "sh:abc0000000:ab"]
    client.scan_iter.assert_called_once_with(match="sh:*")


def test_get_key_values_and_ttls_returns_empty_for_no_keys():
    """No keys means no pipeline round trip is needed."""
    client = MagicMock()

    values, ttls = get_key_values_and_ttls(client, [])

    assert values == []
    assert ttls == []
    client.pipeline.assert_not_called()


def test_get_key_values_and_ttls_uses_one_pipeline_round_trip():
    """Values and TTLs for all keys are fetched via a single pipeline execute."""
    client = MagicMock()
    pipe = MagicMock()
    pipe.execute.return_value = ["https://example.com/a", "https://example.com/b", 100, -1]
    client.pipeline.return_value = pipe

    values, ttls = get_key_values_and_ttls(client, ["sh:a", "sh:b"])

    assert values == ["https://example.com/a", "https://example.com/b"]
    assert ttls == [100, -1]
    client.pipeline.assert_called_once_with(transaction=False)


def test_build_short_link_key_without_variant():
    assert build_short_link_key("abc0000000") == "sh:abc0000000"


def test_build_short_link_key_with_variant():
    assert build_short_link_key("abc0000000", "ab") == "sh:abc0000000:ab"


def test_key_exists_true_and_false():
    client = MagicMock()
    client.exists.return_value = 1
    assert key_exists(client, "sh:abc0000000") is True

    client.exists.return_value = 0
    assert key_exists(client, "sh:abc0000000") is False


def test_set_short_link_without_ttl_omits_px():
    client = MagicMock()
    set_short_link(client, "sh:abc0000000", "https://example.com", None)
    client.set.assert_called_once_with("sh:abc0000000", "https://example.com")


def test_set_short_link_with_ttl_passes_px():
    client = MagicMock()
    set_short_link(client, "sh:abc0000000", "https://example.com", 500)
    client.set.assert_called_once_with("sh:abc0000000", "https://example.com", px=500)


def test_delete_key_returns_true_when_deleted():
    client = MagicMock()
    client.delete.return_value = 1
    assert delete_key(client, "sh:abc0000000") is True


def test_delete_key_returns_false_when_not_found():
    client = MagicMock()
    client.delete.return_value = 0
    assert delete_key(client, "sh:abc0000000") is False


def test_delete_keys_returns_deleted_count():
    client = MagicMock()
    client.delete.return_value = 2
    assert delete_keys(client, ["sh:a", "sh:a:x"]) == 2
    client.delete.assert_called_once_with("sh:a", "sh:a:x")


def test_delete_keys_skips_call_for_empty_list():
    client = MagicMock()
    assert delete_keys(client, []) == 0
    client.delete.assert_not_called()


def test_scan_keys_for_code_uses_code_prefixed_pattern():
    client = MagicMock()
    client.scan_iter.return_value = iter(["sh:abc0000000", "sh:abc0000000:ab"])

    keys = scan_keys_for_code(client, "abc0000000")

    assert keys == ["sh:abc0000000", "sh:abc0000000:ab"]
    client.scan_iter.assert_called_once_with(match="sh:abc0000000*")


def test_add_code_to_index_scores_by_future_expiry_when_ttl_given():
    client = MagicMock()

    add_code_to_index(client, "abc0000000", 60_000)

    client.zadd.assert_called_once()
    args, _ = client.zadd.call_args
    assert args[0] == SHORT_CODE_INDEX_KEY
    score = args[1]["abc0000000"]
    assert score > time.time() * 1000


def test_add_code_to_index_scores_as_infinite_when_no_ttl():
    client = MagicMock()

    add_code_to_index(client, "abc0000000", None)

    client.zadd.assert_called_once_with(SHORT_CODE_INDEX_KEY, {"abc0000000": float("inf")})


def test_remove_code_from_index():
    client = MagicMock()

    remove_code_from_index(client, "abc0000000")

    client.zrem.assert_called_once_with(SHORT_CODE_INDEX_KEY, "abc0000000")


def test_purge_expired_index_entries():
    client = MagicMock()
    client.zremrangebyscore.return_value = 3

    removed = purge_expired_index_entries(client, 1000.0)

    assert removed == 3
    client.zremrangebyscore.assert_called_once_with(SHORT_CODE_INDEX_KEY, "-inf", 1000.0)


def test_get_index_count():
    client = MagicMock()
    client.zcount.return_value = 5

    assert get_index_count(client, 1000.0) == 5
    client.zcount.assert_called_once_with(SHORT_CODE_INDEX_KEY, 1000.0, "+inf")


def test_get_index_page():
    client = MagicMock()
    client.zrangebyscore.return_value = ["abc0000000", "def0000000"]

    codes = get_index_page(client, 1000.0, offset=10, limit=20)

    assert codes == ["abc0000000", "def0000000"]
    client.zrangebyscore.assert_called_once_with(SHORT_CODE_INDEX_KEY, 1000.0, "+inf", start=10, num=20)
