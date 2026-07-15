import pytest
from unittest.mock import MagicMock, patch

from pymongo.errors import PyMongoError

import db.mongo as mongo_module
from db.mongo import MongoDBClient, get_client, get_collection, REQUIRED_COLLECTIONS, TTL_INDEXES


@pytest.fixture(autouse=True)
def reset_singleton():
    """The module-level client singleton must not leak state between tests."""
    mongo_module._instance = None
    yield
    mongo_module._instance = None


@pytest.fixture
def mock_mongo_client_class():
    with patch("db.mongo.MongoClient") as mock_cls:
        yield mock_cls


def _configure_fake_client(mock_cls, existing_collections=()):
    fake_client = MagicMock()
    fake_db = MagicMock()
    fake_db.list_collection_names.return_value = list(existing_collections)
    # A distinct mock per collection name, so tests can assert what happened to
    # e.g. "climate_shelters" without it being conflated with "green_areas".
    collection_mocks = {}
    fake_db.__getitem__.side_effect = lambda name: collection_mocks.setdefault(name, MagicMock())
    fake_client.__getitem__.return_value = fake_db
    fake_client.admin.command.return_value = {"ok": 1}
    mock_cls.return_value = fake_client
    return fake_client, fake_db


# ----------------------------------------------------------------
# MongoDBClient.connect
# ----------------------------------------------------------------

def test_connect_pings_before_selecting_database(mock_mongo_client_class):
    fake_client, fake_db = _configure_fake_client(mock_mongo_client_class)
    client = MongoDBClient("mongodb://fake:27017", db_name="umbra")
    client.connect()

    fake_client.admin.command.assert_called_once_with("ping")
    assert client.db is fake_db


def test_connect_creates_missing_collections(mock_mongo_client_class):
    _, fake_db = _configure_fake_client(mock_mongo_client_class, existing_collections=())
    client = MongoDBClient("mongodb://fake:27017")
    client.connect()

    created = {c.args[0] for c in fake_db.create_collection.call_args_list}
    assert created == set(REQUIRED_COLLECTIONS)


def test_connect_skips_already_existing_collections(mock_mongo_client_class):
    _, fake_db = _configure_fake_client(mock_mongo_client_class, existing_collections=REQUIRED_COLLECTIONS)
    client = MongoDBClient("mongodb://fake:27017")
    client.connect()

    fake_db.create_collection.assert_not_called()


def test_connect_creates_2dsphere_index_on_every_required_collection(mock_mongo_client_class):
    _, fake_db = _configure_fake_client(mock_mongo_client_class)
    client = MongoDBClient("mongodb://fake:27017")
    client.connect()

    for name in REQUIRED_COLLECTIONS:
        geo_calls = [c for c in fake_db[name].create_index.call_args_list
                     if c.args[0] == [("location", "2dsphere")]]
        assert len(geo_calls) == 1, f"expected a 2dsphere index on {name}"


def test_connect_creates_ttl_index_on_collections_that_expire(mock_mongo_client_class):
    _, fake_db = _configure_fake_client(mock_mongo_client_class)
    client = MongoDBClient("mongodb://fake:27017")
    client.connect()

    for name, (field, ttl_seconds) in TTL_INDEXES.items():
        ttl_calls = [c for c in fake_db[name].create_index.call_args_list
                     if c.args[0] == [(field, 1)] and c.kwargs.get("expireAfterSeconds") == ttl_seconds]
        assert len(ttl_calls) == 1, f"expected a TTL index on {name}.{field} ({ttl_seconds}s)"


def test_connect_does_not_create_a_ttl_index_on_collections_outside_the_map(mock_mongo_client_class):
    # climate_shelters is never written by any code path yet (docs/SPEC.md) - it
    # has nothing to expire, so it should only get the 2dsphere index.
    _, fake_db = _configure_fake_client(mock_mongo_client_class)
    client = MongoDBClient("mongodb://fake:27017")
    client.connect()

    assert "climate_shelters" not in TTL_INDEXES
    assert fake_db["climate_shelters"].create_index.call_count == 1


def test_connect_raises_pymongo_error_on_ping_failure(mock_mongo_client_class):
    fake_client = MagicMock()
    fake_client.admin.command.side_effect = PyMongoError("connection refused")
    mock_mongo_client_class.return_value = fake_client

    client = MongoDBClient("mongodb://fake:27017")
    with pytest.raises(PyMongoError):
        client.connect()


# ----------------------------------------------------------------
# MongoDBClient.close
# ----------------------------------------------------------------

def test_close_closes_the_underlying_client(mock_mongo_client_class):
    fake_client, _ = _configure_fake_client(mock_mongo_client_class)
    client = MongoDBClient("mongodb://fake:27017")
    client.connect()
    client.close()

    fake_client.close.assert_called_once()


def test_ensure_collections_raises_if_db_not_set():
    client = MongoDBClient("mongodb://fake:27017")
    with pytest.raises(RuntimeError):
        client._ensure_collections()


# ----------------------------------------------------------------
# get_client / get_collection (module-level singleton)
# ----------------------------------------------------------------

def test_get_client_is_a_singleton(mock_mongo_client_class):
    _configure_fake_client(mock_mongo_client_class)
    first = get_client("mongodb://fake:27017")
    second = get_client("mongodb://fake:27017")

    assert first is second
    mock_mongo_client_class.assert_called_once()


def test_get_collection_raises_if_not_connected():
    with pytest.raises(RuntimeError):
        get_collection("green_areas")


def test_get_collection_returns_the_right_collection(mock_mongo_client_class):
    _, fake_db = _configure_fake_client(mock_mongo_client_class)
    get_client("mongodb://fake:27017")

    collection = get_collection("green_areas")
    assert collection is fake_db["green_areas"]
