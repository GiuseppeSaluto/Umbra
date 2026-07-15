from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from api.services.area_service import get_area_analysis_cached, _bbox_to_polygon

SAMPLE_BBOX = {"min_lon": 10.90, "min_lat": 44.60, "max_lon": 10.95, "max_lat": 44.65}


def _make_collections():
    """One distinct MagicMock per collection name - area_analyses defaults to a
    cache miss (find_one returns None).
    """
    collections = {
        "area_analyses": MagicMock(),
        "green_areas": MagicMock(),
        "heat_islands": MagicMock(),
    }
    collections["area_analyses"].find_one.return_value = None
    return collections


def _patch_get_collection(collections):
    return patch("db.mongo.get_collection", side_effect=lambda name: collections[name])


def _analysis(ndvi_mean=0.1, heat_island_coverage_pct=0.0, bbox=None):
    """A minimal analysis dict below both recording thresholds by default."""
    return {
        "bbox": bbox or SAMPLE_BBOX,
        "ndvi_mean": ndvi_mean,
        "heat_island_coverage_pct": heat_island_coverage_pct,
    }


# ----------------------------------------------------------------
# _bbox_to_polygon
# ----------------------------------------------------------------

def test_bbox_to_polygon_produces_a_closed_ring():
    polygon = _bbox_to_polygon(SAMPLE_BBOX)
    ring = polygon["coordinates"][0]
    assert polygon["type"] == "Polygon"
    assert ring[0] == ring[-1]


def test_bbox_to_polygon_covers_all_four_corners():
    polygon = _bbox_to_polygon(SAMPLE_BBOX)
    ring_points = {tuple(point) for point in polygon["coordinates"][0]}
    expected_corners = {
        (10.90, 44.60), (10.95, 44.60), (10.95, 44.65), (10.90, 44.65),
    }
    assert expected_corners <= ring_points


# ----------------------------------------------------------------
# area_analyses cache (hit / miss / query shape)
# ----------------------------------------------------------------

def test_returns_cached_analysis_without_recomputing_on_fresh_hit(modena_center):
    cached_doc = {
        "location": {"type": "Point", "coordinates": [modena_center["lon"], modena_center["lat"]]},
        "radius_m": 500,
        "analysis": _analysis(ndvi_mean=0.5, heat_island_coverage_pct=10.0),
        "computed_at": datetime.now(timezone.utc),
    }
    collections = _make_collections()
    collections["area_analyses"].find_one.return_value = cached_doc

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis") as fake_compute:
        result = get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    assert result == cached_doc["analysis"]
    fake_compute.assert_not_called()
    # A cache hit must not re-record - it was already recorded when first computed.
    collections["green_areas"].insert_one.assert_not_called()
    collections["heat_islands"].insert_one.assert_not_called()


def test_computes_and_stores_on_cache_miss(modena_center):
    collections = _make_collections()
    fresh_analysis = _analysis()

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis", return_value=fresh_analysis) as fake_compute:
        result = get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    fake_compute.assert_called_once_with(modena_center["lat"], modena_center["lon"], 500)
    assert result == fresh_analysis

    collections["area_analyses"].insert_one.assert_called_once()
    stored_doc = collections["area_analyses"].insert_one.call_args.args[0]
    assert stored_doc["analysis"] == fresh_analysis
    assert stored_doc["radius_m"] == 500
    assert stored_doc["location"] == {
        "type": "Point",
        "coordinates": [modena_center["lon"], modena_center["lat"]],
    }
    assert "computed_at" in stored_doc


def test_cache_lookup_uses_near_filter_and_freshness_cutoff(modena_center):
    collections = _make_collections()

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis", return_value=_analysis()):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    query = collections["area_analyses"].find_one.call_args.args[0]
    assert "$near" in query["location"]
    assert query["radius_m"] == 500
    assert "$gte" in query["computed_at"]


def test_cache_hit_requires_matching_radius(modena_center):
    # A cached analysis for a different radius must not satisfy the query filter -
    # the mocked collection can't evaluate this itself, so this test locks in that
    # the query we build actually constrains on radius_m (regression guard).
    collections = _make_collections()

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis", return_value=_analysis()):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=1000)

    query = collections["area_analyses"].find_one.call_args.args[0]
    assert query["radius_m"] == 1000


# ----------------------------------------------------------------
# green_areas / heat_islands detection recording
# ----------------------------------------------------------------

def test_records_green_area_when_ndvi_mean_exceeds_threshold(modena_center):
    collections = _make_collections()
    analysis = _analysis(ndvi_mean=0.45)

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis", return_value=analysis):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    collections["green_areas"].insert_one.assert_called_once()
    stored = collections["green_areas"].insert_one.call_args.args[0]
    assert stored["ndvi_mean"] == 0.45
    assert stored["location"]["type"] == "Polygon"
    assert "detected_at" in stored


def test_does_not_record_green_area_when_ndvi_mean_at_or_below_threshold(modena_center):
    collections = _make_collections()
    analysis = _analysis(ndvi_mean=0.3)  # exactly at threshold - not "above"

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis", return_value=analysis):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    collections["green_areas"].insert_one.assert_not_called()


def test_records_heat_island_when_coverage_is_above_zero(modena_center):
    collections = _make_collections()
    analysis = _analysis(heat_island_coverage_pct=25.0)

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis", return_value=analysis):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    collections["heat_islands"].insert_one.assert_called_once()
    stored = collections["heat_islands"].insert_one.call_args.args[0]
    assert stored["heat_island_coverage_pct"] == 25.0
    assert stored["location"]["type"] == "Polygon"
    assert "detected_at" in stored


def test_does_not_record_heat_island_when_coverage_is_zero(modena_center):
    collections = _make_collections()
    analysis = _analysis(heat_island_coverage_pct=0.0)

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis", return_value=analysis):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    collections["heat_islands"].insert_one.assert_not_called()


def test_records_both_when_both_thresholds_are_exceeded(modena_center):
    collections = _make_collections()
    analysis = _analysis(ndvi_mean=0.6, heat_island_coverage_pct=15.0)

    with _patch_get_collection(collections), \
         patch("api.services.area_service.get_area_analysis", return_value=analysis):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    collections["green_areas"].insert_one.assert_called_once()
    collections["heat_islands"].insert_one.assert_called_once()
