from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from api.services.area_service import get_area_analysis_cached


def _fake_collection(find_one_result=None):
    collection = MagicMock()
    collection.find_one.return_value = find_one_result
    return collection


def test_returns_cached_analysis_without_recomputing_on_fresh_hit(modena_center):
    cached_doc = {
        "location": {"type": "Point", "coordinates": [modena_center["lon"], modena_center["lat"]]},
        "radius_m": 500,
        "analysis": {"ndvi_mean": 0.5, "heat_island_coverage_pct": 10.0},
        "computed_at": datetime.now(timezone.utc),
    }
    collection = _fake_collection(find_one_result=cached_doc)

    with patch("db.mongo.get_collection", return_value=collection), \
         patch("api.services.area_service.get_area_analysis") as fake_compute:
        result = get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    assert result == cached_doc["analysis"]
    fake_compute.assert_not_called()


def test_computes_and_stores_on_cache_miss(modena_center):
    collection = _fake_collection(find_one_result=None)
    fresh_analysis = {"ndvi_mean": 0.42, "heat_island_coverage_pct": 5.0}

    with patch("db.mongo.get_collection", return_value=collection), \
         patch("api.services.area_service.get_area_analysis", return_value=fresh_analysis) as fake_compute:
        result = get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    fake_compute.assert_called_once_with(modena_center["lat"], modena_center["lon"], 500)
    assert result == fresh_analysis

    collection.insert_one.assert_called_once()
    stored_doc = collection.insert_one.call_args.args[0]
    assert stored_doc["analysis"] == fresh_analysis
    assert stored_doc["radius_m"] == 500
    assert stored_doc["location"] == {
        "type": "Point",
        "coordinates": [modena_center["lon"], modena_center["lat"]],
    }
    assert "computed_at" in stored_doc


def test_cache_lookup_uses_near_filter_and_freshness_cutoff(modena_center):
    collection = _fake_collection(find_one_result=None)

    with patch("db.mongo.get_collection", return_value=collection), \
         patch("api.services.area_service.get_area_analysis", return_value={}):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=500)

    query = collection.find_one.call_args.args[0]
    assert "$near" in query["location"]
    assert query["radius_m"] == 500
    assert "$gte" in query["computed_at"]


def test_cache_hit_requires_matching_radius(modena_center):
    # A cached analysis for a different radius must not satisfy the query filter -
    # the mocked collection can't evaluate this itself, so this test locks in that
    # the query we build actually constrains on radius_m (regression guard).
    collection = _fake_collection(find_one_result=None)

    with patch("db.mongo.get_collection", return_value=collection), \
         patch("api.services.area_service.get_area_analysis", return_value={}):
        get_area_analysis_cached(modena_center["lat"], modena_center["lon"], radius_m=1000)

    query = collection.find_one.call_args.args[0]
    assert query["radius_m"] == 1000
