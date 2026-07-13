import json

import pytest
from unittest.mock import MagicMock, patch

import db.valkey_cache as valkey_module
from db.valkey_cache import get_client, get_cached_json, set_cached_json


@pytest.fixture(autouse=True)
def reset_singleton():
    """The module-level client singleton must not leak state between tests."""
    valkey_module._instance = None
    yield
    valkey_module._instance = None


@pytest.fixture
def mock_redis_class():
    with patch("db.valkey_cache.redis.Redis") as mock_cls:
        yield mock_cls


def _configure_fake_client(mock_cls):
    fake_client = MagicMock()
    mock_cls.from_url.return_value = fake_client
    return fake_client


# ----------------------------------------------------------------
# get_client
# ----------------------------------------------------------------

def test_get_client_pings_on_connect(mock_redis_class):
    fake_client = _configure_fake_client(mock_redis_class)
    client = get_client("redis://localhost:6379/0")

    fake_client.ping.assert_called_once()
    assert client is fake_client


def test_get_client_is_a_singleton(mock_redis_class):
    _configure_fake_client(mock_redis_class)
    first = get_client("redis://localhost:6379/0")
    second = get_client("redis://localhost:6379/0")

    assert first is second
    mock_redis_class.from_url.assert_called_once()


# ----------------------------------------------------------------
# get_cached_json / set_cached_json
# ----------------------------------------------------------------

def test_get_cached_json_returns_none_on_miss(mock_redis_class):
    fake_client = _configure_fake_client(mock_redis_class)
    fake_client.get.return_value = None
    get_client("redis://localhost:6379/0")

    assert get_cached_json("some-key") is None


def test_get_cached_json_deserializes_stored_value(mock_redis_class):
    fake_client = _configure_fake_client(mock_redis_class)
    fake_client.get.return_value = json.dumps({"ndvi_mean": 0.42})
    get_client("redis://localhost:6379/0")

    assert get_cached_json("some-key") == {"ndvi_mean": 0.42}


def test_set_cached_json_serializes_value_and_sets_ttl(mock_redis_class):
    fake_client = _configure_fake_client(mock_redis_class)
    get_client("redis://localhost:6379/0")

    set_cached_json("some-key", {"ndvi_mean": 0.42}, ttl_seconds=900)

    fake_client.set.assert_called_once_with("some-key", json.dumps({"ndvi_mean": 0.42}), ex=900)


def test_get_cached_json_raises_if_not_connected():
    with pytest.raises(RuntimeError):
        get_cached_json("some-key")


def test_set_cached_json_raises_if_not_connected():
    with pytest.raises(RuntimeError):
        set_cached_json("some-key", {}, ttl_seconds=900)
