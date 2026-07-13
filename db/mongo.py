"""MongoDB connection and query layer (2dsphere index)."""

from pymongo import MongoClient
from pymongo.collection import Collection

from processing.geo import validate_coordinates

_client: MongoClient | None = None


def get_client(uri: str) -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(uri)
    return _client


def get_collection(name: str) -> Collection:
    """Return the requested MongoDB collection (refuges, green areas, heat islands)."""
    raise NotImplementedError


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
