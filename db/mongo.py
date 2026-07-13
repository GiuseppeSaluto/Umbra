"""MongoDB connection and query layer (2dsphere index)."""

from pymongo import MongoClient
from pymongo.collection import Collection

_client: MongoClient | None = None


def get_client(uri: str) -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(uri)
    return _client


def get_collection(name: str) -> Collection:
    """Return the requested MongoDB collection (refuges, green areas, heat islands)."""
    raise NotImplementedError
