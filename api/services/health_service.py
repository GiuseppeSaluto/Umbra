"""Health checks for external dependencies."""

import db.mongo as db_mongo
from pymongo.errors import PyMongoError


def check_mongo_connectivity() -> bool:
    """Return True if MongoDB is reachable, False otherwise."""
    try:
        db_mongo.get_collection("green_areas").count_documents({})
        return True
    except (PyMongoError, RuntimeError):
        return False
