"""Pure geographic math - coordinate validation, distance, bounding box. Phase 1 - MVP."""

import math

EARTH_RADIUS_M = 6_371_000.0


def validate_coordinates(lat: float, lon: float) -> None:
    """Raise ValueError if lat/lon are outside their physically valid ranges."""
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"latitude must be between -90 and 90, got {lat}")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"longitude must be between -180 and 180, got {lon}")


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in meters between two lat/lon points."""
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)

    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def bbox_from_point(lat: float, lon: float, radius_m: float) -> dict:
    """Return a bounding box {min_lon, min_lat, max_lon, max_lat} around a center point.

    Undefined exactly at the poles (longitude spacing collapses to zero there).
    """
    validate_coordinates(lat, lon)
    if lat == 90.0 or lat == -90.0:
        raise ValueError("bounding box is undefined at the poles")

    lat_delta_deg = math.degrees(radius_m / EARTH_RADIUS_M)
    lon_delta_deg = math.degrees(radius_m / (EARTH_RADIUS_M * math.cos(math.radians(lat))))

    return {
        "min_lon": lon - lon_delta_deg,
        "min_lat": lat - lat_delta_deg,
        "max_lon": lon + lon_delta_deg,
        "max_lat": lat + lat_delta_deg,
    }
