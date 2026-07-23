import pytest

from api.services.area_service import get_area_analysis
from processing.heat import heat_island_coverage_pct

# ----------------------------------------------------------------
# api/services/area_service.py
# ----------------------------------------------------------------


def test_get_area_analysis_returns_expected_keys(mock_sentinel, modena_center):
    result = get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert set(result.keys()) == {
        "bbox",
        "ndvi_mean",
        "ndvi_min",
        "ndvi_max",
        "heat_island_coverage_pct",
        "green_bbox",
        "heat_bbox",
        "acquisition_date",
        "cloud_coverage_pct",
        "resolution_m_ndvi",
        "resolution_m_lst",
        "source",
    }


def test_get_area_analysis_ndvi_mean_matches_precomputed_sample(mock_sentinel, modena_center, sample_ndvi_array):
    result = get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert result["ndvi_mean"] == pytest.approx(float(sample_ndvi_array.mean()), rel=1e-5)


def test_get_area_analysis_heat_pct_matches_manual_calculation(mock_sentinel, modena_center, sample_lst):
    result = get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)
    expected = heat_island_coverage_pct(sample_lst)
    assert result["heat_island_coverage_pct"] == pytest.approx(expected)


def test_get_area_analysis_bbox_passthrough_from_sentinel_response(mock_sentinel, modena_center):
    result = get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert result["bbox"] == mock_sentinel["bbox"]


def test_get_area_analysis_acquisition_date_is_isoformat_string(mock_sentinel, modena_center):
    result = get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert result["acquisition_date"] == mock_sentinel["acquisition_date"].isoformat()


def test_get_area_analysis_rejects_invalid_coordinates():
    with pytest.raises(ValueError):
        get_area_analysis(200.0, 0.0, radius_m=500)


def test_get_area_analysis_rejects_non_positive_radius(modena_center):
    with pytest.raises(ValueError):
        get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=0)


# ----------------------------------------------------------------
# GET /api/area
# ----------------------------------------------------------------


def test_area_endpoint_returns_200_with_expected_json(client, modena_center):
    response = client.get(
        "/api/area", query_string={"lat": modena_center["lat"], "lon": modena_center["lon"], "radius_m": 500}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert -1.0 <= data["ndvi_mean"] <= 1.0
    assert 0.0 <= data["heat_island_coverage_pct"] <= 100.0


def test_area_endpoint_uses_default_radius_when_omitted(client, modena_center):
    response = client.get("/api/area", query_string={"lat": modena_center["lat"], "lon": modena_center["lon"]})
    assert response.status_code == 200


def test_area_endpoint_400_on_missing_lat(client, modena_center):
    response = client.get("/api/area", query_string={"lon": modena_center["lon"]})
    assert response.status_code == 400


def test_area_endpoint_400_on_non_numeric_lat(client, modena_center):
    response = client.get("/api/area", query_string={"lat": "not-a-number", "lon": modena_center["lon"]})
    assert response.status_code == 400


def test_area_endpoint_400_on_out_of_range_latitude(client, modena_center):
    response = client.get("/api/area", query_string={"lat": 200.0, "lon": modena_center["lon"]})
    assert response.status_code == 400


def test_area_endpoint_400_on_non_positive_radius(client, modena_center):
    response = client.get(
        "/api/area",
        query_string={"lat": modena_center["lat"], "lon": modena_center["lon"], "radius_m": -10},
    )
    assert response.status_code == 400


def test_area_endpoint_accepts_comma_decimal_separator(client, modena_center):
    response = client.get("/api/area", query_string={"lat": "44,6471", "lon": "10,9252"})
    assert response.status_code == 200


def test_area_endpoint_accepts_surrounding_whitespace(client, modena_center):
    response = client.get("/api/area", query_string={"lat": " 44.6471 ", "lon": " 10.9252 "})
    assert response.status_code == 200
