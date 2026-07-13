"""Valkey cache layer (open source Redis fork) - a fast response cache that sits
in front of MongoDB. Does not replace MongoDB, only serves frequent repeat
queries faster; anything not found here falls through to Mongo (see
api/services/area_service.py::get_area_analysis_cached).
"""

import json
import logging

import redis

logger = logging.getLogger(__name__)

_instance: redis.Redis | None = None


def get_client(url: str) -> redis.Redis:
    """Return the module-level Valkey client, connecting lazily on first call."""
    global _instance
    if _instance is None:
        _instance = redis.Redis.from_url(url, decode_responses=True)
        _instance.ping()
        logger.info("Connected to Valkey at %s", url)
    return _instance


def get_cached_json(key: str):
    """Return the cached value for key, deserialized from JSON, or None on a miss."""
    if _instance is None:
        raise RuntimeError("Valkey is not connected yet. Call get_client(url) first.")
    raw = _instance.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def set_cached_json(key: str, value, ttl_seconds: int) -> None:
    """Store value as JSON under key, expiring after ttl_seconds."""
    if _instance is None:
        raise RuntimeError("Valkey is not connected yet. Call get_client(url) first.")
    _instance.set(key, json.dumps(value), ex=ttl_seconds)
