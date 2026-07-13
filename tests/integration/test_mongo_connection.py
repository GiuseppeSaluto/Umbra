import pytest
from unittest.mock import MagicMock, patch

from pymongo.errors import PyMongoError

import db.mongo as mongo_module
from db.mongo import MongoDBClient, get_client, get_collection, REQUIRED_COLLECTIONS


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

    collection_mock = fake_db.__getitem__.return_value
    assert collection_mock.create_index.call_count == len(REQUIRED_COLLECTIONS)
    for call_args in collection_mock.create_index.call_args_list:
        assert call_args.args[0] == [("location", "2dsphere")]


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
    assert collection is fake_db.__getitem__.return_value
