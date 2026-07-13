import pytest

from processing.geo import validate_coordinates, haversine_distance_m, bbox_from_point


# ----------------------------------------------------------------
# validate_coordinates
# ----------------------------------------------------------------

def test_validate_coordinates_accepts_valid_point(modena_center):
    validate_coordinates(modena_center["lat"], modena_center["lon"])  # must not raise


@pytest.mark.parametrize("lat", [90.0, -90.0, 44.6471])
def test_validate_coordinates_accepts_latitude_boundaries(lat):
    validate_coordinates(lat, 0.0)  # must not raise


@pytest.mark.parametrize("lat", [90.1, -90.1, 1000.0])
def test_validate_coordinates_rejects_out_of_range_latitude(lat):
    with pytest.raises(ValueError):
        validate_coordinates(lat, 0.0)


@pytest.mark.parametrize("lon", [180.1, -180.1, 1000.0])
def test_validate_coordinates_rejects_out_of_range_longitude(lon):
    with pytest.raises(ValueError):
        validate_coordinates(0.0, lon)


# ----------------------------------------------------------------
# haversine_distance_m
# ----------------------------------------------------------------

def test_haversine_distance_is_zero_for_identical_points(modena_center):
    d = haversine_distance_m(
        modena_center["lat"], modena_center["lon"],
        modena_center["lat"], modena_center["lon"],
    )
    assert d == pytest.approx(0.0, abs=1e-6)


def test_haversine_distance_one_degree_longitude_at_equator():
    # 1 degree of longitude at the equator is ~111.19 km (mean Earth radius 6371 km).
    d = haversine_distance_m(0.0, 0.0, 0.0, 1.0)
    assert d == pytest.approx(111_194.9, rel=0.01)


def test_haversine_distance_shrinks_with_latitude_due_to_meridian_convergence():
    # The same 1-degree longitude offset spans a shorter distance away from the equator.
    d_equator = haversine_distance_m(0.0, 0.0, 0.0, 1.0)
    d_45 = haversine_distance_m(45.0, 0.0, 45.0, 1.0)
    assert d_45 < d_equator
    assert d_45 == pytest.approx(d_equator * 0.70711, rel=0.01)


def test_haversine_distance_is_symmetric(modena_center):
    other_lat, other_lon = 44.6558, 10.9235
    d_forward = haversine_distance_m(modena_center["lat"], modena_center["lon"], other_lat, other_lon)
    d_backward = haversine_distance_m(other_lat, other_lon, modena_center["lat"], modena_center["lon"])
    assert d_forward == pytest.approx(d_backward)


# ----------------------------------------------------------------
# bbox_from_point
# ----------------------------------------------------------------

def test_bbox_contains_center_point(modena_center):
    bbox = bbox_from_point(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert bbox["min_lat"] < modena_center["lat"] < bbox["max_lat"]
    assert bbox["min_lon"] < modena_center["lon"] < bbox["max_lon"]


def test_bbox_has_expected_keys(modena_center):
    bbox = bbox_from_point(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert set(bbox.keys()) == {"min_lon", "min_lat", "max_lon", "max_lat"}


def test_bbox_grows_with_radius(modena_center):
    small = bbox_from_point(modena_center["lat"], modena_center["lon"], radius_m=250)
    large = bbox_from_point(modena_center["lat"], modena_center["lon"], radius_m=1000)
    small_span = small["max_lat"] - small["min_lat"]
    large_span = large["max_lat"] - large["min_lat"]
    assert large_span > small_span


def test_bbox_is_roughly_square_at_equator():
    bbox = bbox_from_point(0.0, 0.0, radius_m=1000)
    lat_span = bbox["max_lat"] - bbox["min_lat"]
    lon_span = bbox["max_lon"] - bbox["min_lon"]
    assert lat_span == pytest.approx(lon_span, rel=0.01)


def test_bbox_longitude_span_widens_away_from_equator():
    # Meridians converge toward the poles, so the same radius covers a wider
    # longitude span at high latitude than at the equator.
    bbox_equator = bbox_from_point(0.0, 0.0, radius_m=1000)
    bbox_high_lat = bbox_from_point(60.0, 0.0, radius_m=1000)
    lon_span_equator = bbox_equator["max_lon"] - bbox_equator["min_lon"]
    lon_span_high_lat = bbox_high_lat["max_lon"] - bbox_high_lat["min_lon"]
    assert lon_span_high_lat > lon_span_equator


def test_bbox_rejects_poles():
    with pytest.raises(ValueError):
        bbox_from_point(90.0, 0.0, radius_m=500)


def test_bbox_rejects_invalid_coordinates():
    with pytest.raises(ValueError):
        bbox_from_point(200.0, 0.0, radius_m=500)
