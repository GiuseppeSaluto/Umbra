"""Area analysis - ties together Sentinel-2 fetch, NDVI, and heat island computation."""

import logging
from datetime import datetime, timedelta, timezone

import db.mongo as db_mongo
import db.valkey_cache as valkey_cache
import processing.sentinel as sentinel_module
from processing.geo import validate_coordinates
from processing.heat import heat_island_coverage_pct
from processing.ndvi import calculate_ndvi

logger = logging.getLogger(__name__)

# How close a cached analysis's center must be to the requested point to be reused.
CACHE_PROXIMITY_M = 100
# NDVI/LST source imagery changes on the order of days (Sentinel-2/3 revisit time),
# so a cached analysis is considered fresh for this long.
CACHE_FRESHNESS = timedelta(hours=24)
# Valkey is a fast, short-TTL cache in front of MongoDB (docs/SPEC.md section 5:
# "served from Valkey for N minutes") - it's optional, a connection failure here
# must never break the request, only fall back to the MongoDB-backed cache below.
VALKEY_TTL_SECONDS = 900
# Same NDVI threshold used in processing/ndvi.py's spec (docs/SPEC.md section 8):
# above this, an area counts as dense vegetation and gets recorded as a green area.
GREEN_AREA_NDVI_THRESHOLD = 0.3
# Any detected heat-island pixel coverage is recorded - LST resolution is already
# coarse (~1km, see processing/sentinel.py), so a stricter threshold would just
# hide genuine detections in small query areas.
HEAT_ISLAND_COVERAGE_THRESHOLD_PCT = 0.0


def get_area_analysis(lat: float, lon: float, radius_m: float) -> dict:
    """Return an NDVI/LST summary for the area centered on (lat, lon)."""
    validate_coordinates(lat, lon)
    if radius_m <= 0:
        raise ValueError(f"radius_m must be positive, got {radius_m}")

    data = sentinel_module.fetch_area_data(lat, lon, radius_m)

    ndvi = calculate_ndvi(data["ndvi_b4"], data["ndvi_b8"])
    heat_pct = heat_island_coverage_pct(data["lst"])

    return {
        "bbox": data["bbox"],
        "ndvi_mean": float(ndvi.mean()),
        "ndvi_min": float(ndvi.min()),
        "ndvi_max": float(ndvi.max()),
        "heat_island_coverage_pct": heat_pct,
        "acquisition_date": data["acquisition_date"].isoformat(),
        "cloud_coverage_pct": data["cloud_coverage_pct"],
        "resolution_m_ndvi": data["resolution_m_ndvi"],
        "resolution_m_lst": data["resolution_m_lst"],
        "source": data["source"],
    }


def _bbox_to_polygon(bbox: dict) -> dict:
    """Convert a {min_lon, min_lat, max_lon, max_lat} bbox into a closed GeoJSON
    Polygon ring, wound counter-clockwise as required by MongoDB's 2dsphere index.
    """
    min_lon, min_lat = bbox["min_lon"], bbox["min_lat"]
    max_lon, max_lat = bbox["max_lon"], bbox["max_lat"]
    return {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]],
    }


def _record_green_area_if_detected(analysis: dict) -> None:
    if analysis["ndvi_mean"] <= GREEN_AREA_NDVI_THRESHOLD:
        return
    db_mongo.get_collection("green_areas").insert_one({
        "location": _bbox_to_polygon(analysis["bbox"]),
        "ndvi_mean": analysis["ndvi_mean"],
        "detected_at": datetime.now(timezone.utc),
    })


def _record_heat_island_if_detected(analysis: dict) -> None:
    if analysis["heat_island_coverage_pct"] <= HEAT_ISLAND_COVERAGE_THRESHOLD_PCT:
        return
    db_mongo.get_collection("heat_islands").insert_one({
        "location": _bbox_to_polygon(analysis["bbox"]),
        "heat_island_coverage_pct": analysis["heat_island_coverage_pct"],
        "detected_at": datetime.now(timezone.utc),
    })


def _valkey_cache_key(lat: float, lon: float, radius_m: float) -> str:
    return f"area:{round(lat, 4)}:{round(lon, 4)}:{round(radius_m)}"


def _try_get_from_valkey(key: str):
    """Valkey is an optional fast-path cache - any failure (not connected,
    connection dropped, ...) must degrade to a cache miss, never raise.
    """
    try:
        return valkey_cache.get_cached_json(key)
    except Exception:
        logger.warning("Valkey unavailable on read, falling back to MongoDB", exc_info=True)
        return None


def _try_set_in_valkey(key: str, value: dict) -> None:
    try:
        valkey_cache.set_cached_json(key, value, ttl_seconds=VALKEY_TTL_SECONDS)
    except Exception:
        logger.warning("Valkey unavailable on write, skipping fast-cache population", exc_info=True)


def get_area_analysis_cached(lat: float, lon: float, radius_m: float) -> dict:
    """Return a recent cached analysis near (lat, lon) if one exists, otherwise
    compute one via get_area_analysis(), store it in MongoDB for next time, and
    record it as a detected green area / heat island if it qualifies.

    Checks Valkey first (fast, exact-match, short TTL), then MongoDB (slower,
    geospatially fuzzy via $near, 24h freshness) before falling back to a real
    Sentinel Hub fetch.
    """
    valkey_key = _valkey_cache_key(lat, lon, radius_m)
    from_valkey = _try_get_from_valkey(valkey_key)
    if from_valkey is not None:
        return from_valkey

    collection = db_mongo.get_collection("area_analyses")

    near_filter = db_mongo.build_near_filter(lat, lon, radius_m=CACHE_PROXIMITY_M)
    cutoff = datetime.now(timezone.utc) - CACHE_FRESHNESS
    query = {**near_filter, "radius_m": radius_m, "computed_at": {"$gte": cutoff}}

    cached = collection.find_one(query)
    if cached is not None:
        _try_set_in_valkey(valkey_key, cached["analysis"])
        return cached["analysis"]

    analysis = get_area_analysis(lat, lon, radius_m)
    collection.insert_one({
        "location": {"type": "Point", "coordinates": [lon, lat]},
        "radius_m": radius_m,
        "analysis": analysis,
        "computed_at": datetime.now(timezone.utc),
    })
    _record_green_area_if_detected(analysis)
    _record_heat_island_if_detected(analysis)
    _try_set_in_valkey(valkey_key, analysis)
    return analysis
