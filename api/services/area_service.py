"""Area analysis - ties together Sentinel-2 fetch, NDVI, and heat island computation."""

from datetime import datetime, timedelta, timezone

import db.mongo as db_mongo
import processing.sentinel as sentinel_module
from processing.geo import validate_coordinates
from processing.heat import heat_island_coverage_pct
from processing.ndvi import calculate_ndvi

# How close a cached analysis's center must be to the requested point to be reused.
CACHE_PROXIMITY_M = 100
# NDVI/LST source imagery changes on the order of days (Sentinel-2/3 revisit time),
# so a cached analysis is considered fresh for this long.
CACHE_FRESHNESS = timedelta(hours=24)


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


def get_area_analysis_cached(lat: float, lon: float, radius_m: float) -> dict:
    """Return a recent cached analysis near (lat, lon) if one exists, otherwise
    compute one via get_area_analysis() and store it in MongoDB for next time.
    """
    collection = db_mongo.get_collection("area_analyses")

    near_filter = db_mongo.build_near_filter(lat, lon, radius_m=CACHE_PROXIMITY_M)
    cutoff = datetime.now(timezone.utc) - CACHE_FRESHNESS
    query = {**near_filter, "radius_m": radius_m, "computed_at": {"$gte": cutoff}}

    cached = collection.find_one(query)
    if cached is not None:
        return cached["analysis"]

    analysis = get_area_analysis(lat, lon, radius_m)
    collection.insert_one({
        "location": {"type": "Point", "coordinates": [lon, lat]},
        "radius_m": radius_m,
        "analysis": analysis,
        "computed_at": datetime.now(timezone.utc),
    })
    return analysis
