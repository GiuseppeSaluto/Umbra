"""Area analysis - ties together Sentinel-2 fetch, NDVI, and heat island computation."""

import logging
from datetime import datetime, timedelta, timezone

import db.mongo as db_mongo
import processing.sentinel as sentinel_module
from processing.geo import bbox_of_mask, validate_coordinates
from processing.heat import heat_island_coverage_pct, is_heat_island
from processing.ndvi import calculate_ndvi

logger = logging.getLogger(__name__)

# How close a cached analysis's center must be to the requested point to be reused.
CACHE_PROXIMITY_M = 100
DETECTION_DEDUP_RADIUS_M = 300
CACHE_FRESHNESS = timedelta(hours=24)
GREEN_AREA_NDVI_THRESHOLD = 0.3
HEAT_ISLAND_COVERAGE_THRESHOLD_PCT = 0.0
NEARBY_DETECTIONS_LIMIT = 50


def get_area_analysis(lat: float, lon: float, radius_m: float) -> dict:
    """Return an NDVI/LST summary for the area centered on (lat, lon)."""
    validate_coordinates(lat, lon)
    if radius_m <= 0:
        raise ValueError(f"radius_m must be positive, got {radius_m}")

    data = sentinel_module.fetch_area_data(lat, lon, radius_m)

    ndvi = calculate_ndvi(data["ndvi_b4"], data["ndvi_b8"])
    heat_pct = heat_island_coverage_pct(data["lst"]) if data["lst"] is not None else None

    green_bbox = bbox_of_mask(ndvi > GREEN_AREA_NDVI_THRESHOLD, data["bbox"])
    heat_bbox = bbox_of_mask(is_heat_island(data["lst"]), data["bbox"]) if data["lst"] is not None else None

    return {
        "bbox": data["bbox"],
        "ndvi_mean": float(ndvi.mean()),
        "ndvi_min": float(ndvi.min()),
        "ndvi_max": float(ndvi.max()),
        "heat_island_coverage_pct": heat_pct,
        "green_bbox": green_bbox,
        "heat_bbox": heat_bbox,
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


def _upsert_detection(collection_name: str, bbox: dict, fields: dict) -> None:
    collection = db_mongo.get_collection(collection_name)
    center_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
    center_lon = (bbox["min_lon"] + bbox["max_lon"]) / 2
    near_filter = db_mongo.build_near_filter(center_lat, center_lon, radius_m=DETECTION_DEDUP_RADIUS_M)

    document = {"location": _bbox_to_polygon(bbox), "detected_at": datetime.now(timezone.utc), **fields}
    existing = collection.find_one(near_filter)
    if existing is not None:
        collection.update_one({"_id": existing["_id"]}, {"$set": document})
    else:
        collection.insert_one(document)


def _record_green_area_if_detected(analysis: dict) -> None:
    if analysis["ndvi_mean"] <= GREEN_AREA_NDVI_THRESHOLD:
        return
    bbox = analysis["green_bbox"] or analysis["bbox"]
    _upsert_detection("green_areas", bbox, {"ndvi_mean": analysis["ndvi_mean"]})


def _record_heat_island_if_detected(analysis: dict) -> None:
    heat_pct = analysis["heat_island_coverage_pct"]
    if heat_pct is None or heat_pct <= HEAT_ISLAND_COVERAGE_THRESHOLD_PCT:
        return
    bbox = analysis["heat_bbox"] or analysis["bbox"]
    _upsert_detection("heat_islands", bbox, {"heat_island_coverage_pct": heat_pct})


def get_nearby_detections(lat: float, lon: float, radius_m: float) -> dict:
    """Return past green area / heat island detections near (lat, lon), for
    rendering as map layers (see map/renderer.py). Uses the same $near filter
    already built/tested for the area_analyses cache lookup.
    """
    near_filter = db_mongo.build_near_filter(lat, lon, radius_m=radius_m)

    green_areas = list(
        db_mongo.get_collection("green_areas").find(near_filter, limit=NEARBY_DETECTIONS_LIMIT)
    )
    heat_islands = list(
        db_mongo.get_collection("heat_islands").find(near_filter, limit=NEARBY_DETECTIONS_LIMIT)
    )
    return {"green_areas": green_areas, "heat_islands": heat_islands}


def get_area_analysis_cached(lat: float, lon: float, radius_m: float) -> dict:
    """Return a recent cached analysis near (lat, lon) if one exists, otherwise
    compute one via get_area_analysis(), store it in MongoDB for next time, and
    record it as a detected green area / heat island if it qualifies.
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
    _record_green_area_if_detected(analysis)
    _record_heat_island_if_detected(analysis)
    return analysis
