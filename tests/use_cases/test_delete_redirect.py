"""Tests for the delete_redirect use-case."""

from unittest.mock import MagicMock

import pytest

from app.core.errors import RedirectNotFoundError
from app.use_cases.delete_redirect import delete_redirect


def test_delete_redirect_deletes_base_key():
    client = MagicMock()
    client.exists.return_value = 1

    delete_redirect(redis_client=client, code="aB3dE5gH7j", variant=None)

    client.delete.assert_called_once_with("sh:aB3dE5gH7j")


def test_delete_redirect_deletes_variant_key():
    client = MagicMock()
    client.exists.return_value = 1

    delete_redirect(redis_client=client, code="aB3dE5gH7j", variant="ab")

    client.delete.assert_called_once_with("sh:aB3dE5gH7j:ab")


def test_delete_redirect_raises_when_missing():
    client = MagicMock()
    client.exists.return_value = 0

    with pytest.raises(RedirectNotFoundError):
        delete_redirect(redis_client=client, code="aB3dE5gH7j", variant=None)

    client.delete.assert_not_called()
