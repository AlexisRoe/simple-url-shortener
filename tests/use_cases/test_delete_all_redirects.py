"""Tests for the delete_all_redirects use-case."""

from unittest.mock import MagicMock

import pytest

from app.core.errors import RedirectNotFoundError
from app.use_cases.delete_all_redirects import delete_all_redirects


def test_delete_all_redirects_deletes_base_and_variant_keys():
    client = MagicMock()
    client.exists.return_value = 1
    client.scan_iter.return_value = iter(["sh:aB3dE5gH7j", "sh:aB3dE5gH7j:ab", "sh:aB3dE5gH7j:cd"])

    delete_all_redirects(redis_client=client, code="aB3dE5gH7j")

    client.delete.assert_called_once_with("sh:aB3dE5gH7j", "sh:aB3dE5gH7j:ab", "sh:aB3dE5gH7j:cd")


def test_delete_all_redirects_raises_when_code_missing():
    client = MagicMock()
    client.exists.return_value = 0

    with pytest.raises(RedirectNotFoundError):
        delete_all_redirects(redis_client=client, code="aB3dE5gH7j")

    client.delete.assert_not_called()
