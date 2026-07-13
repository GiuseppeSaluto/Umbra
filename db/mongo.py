"""MongoDB connection and query layer (2dsphere index)."""

import logging

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from processing.geo import validate_coordinates

logger = logging.getLogger(__name__)

REQUIRED_COLLECTIONS = ("green_areas", "heat_islands", "climate_shelters", "area_analyses")


class MongoDBClient:
    """Owns the MongoDB connection for the `umbra` database."""

    def __init__(self, uri: str, db_name: str = "umbra"):
        self.uri = uri
        self.db_name = db_name
        self.client: MongoClient | None = None
        self.db: Database | None = None

    def connect(self) -> None:
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=3000)
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]

            logger.info("Connected to MongoDB at %s, using DB '%s'", self.uri, self.db_name)
            self._ensure_collections()
        except PyMongoError:
            logger.critical("Failed to initialize MongoDB", exc_info=True)
            raise

    def _ensure_collections(self) -> None:
        if self.db is None:
            raise RuntimeError("Database not initialized. Call connect() first.")

        existing = self.db.list_collection_names()
        for name in REQUIRED_COLLECTIONS:
            if name not in existing:
                self.db.create_collection(name)
                logger.info("Created MongoDB collection '%s'", name)
            self.db[name].create_index([("location", "2dsphere")])

    def close(self) -> None:
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


_instance: MongoDBClient | None = None


def get_client(uri: str, db_name: str = "umbra") -> MongoDBClient:
    """Return the module-level MongoDBClient, connecting lazily on first call."""
    global _instance
    if _instance is None:
        _instance = MongoDBClient(uri, db_name)
        _instance.connect()
    return _instance


def get_collection(name: str) -> Collection:
    """Return the requested MongoDB collection (green_areas, heat_islands, climate_shelters)."""
    if _instance is None or _instance.db is None:
        raise RuntimeError("MongoDB is not connected yet. Call get_client(uri) first.")
    return _instance.db[name]


def build_near_filter(lat: float, lon: float, radius_m: float, field: str = "location") -> dict:
    """Build a $near filter - documents within radius_m of (lat, lon), nearest first."""
    validate_coordinates(lat, lon)
    if radius_m <= 0:
        raise ValueError(f"radius_m must be positive, got {radius_m}")

    return {
        field: {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                "$maxDistance": radius_m,
            }
        }
    }


def build_geo_within_filter(polygon: dict, field: str = "location") -> dict:
    """Build a $geoWithin filter - documents whose location falls inside the given polygon."""
    if polygon.get("type") != "Polygon":
        raise ValueError(f"expected a GeoJSON Polygon, got type={polygon.get('type')!r}")
    if "coordinates" not in polygon:
        raise ValueError("polygon is missing 'coordinates'")

    return {
        field: {
            "$geoWithin": {
                "$geometry": polygon
            }
        }
    }


def build_geo_intersects_filter(geometry: dict, field: str = "location") -> dict:
    """Build a $geoIntersects filter - documents whose geometry intersects the
    given GeoJSON geometry (Point, LineString, Polygon, ...). Unlike $geoWithin,
    this also matches partial overlaps (e.g. a heat island polygon that only
    partially overlaps a green area polygon), not just full containment.
    """
    if not geometry.get("type"):
        raise ValueError("geometry is missing 'type'")
    if "coordinates" not in geometry:
        raise ValueError("geometry is missing 'coordinates'")

    return {
        field: {
            "$geoIntersects": {
                "$geometry": geometry
            }
        }
    }
