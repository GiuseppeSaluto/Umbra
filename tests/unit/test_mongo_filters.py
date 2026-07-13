import pytest

from db.mongo import build_near_filter, build_geo_within_filter


# ----------------------------------------------------------------
# build_near_filter
# ----------------------------------------------------------------

def test_build_near_filter_structure(modena_center):
    filt = build_near_filter(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert filt == {
        "location": {
            "$near": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [modena_center["lon"], modena_center["lat"]],
                },
                "$maxDistance": 500,
            }
        }
    }


def test_build_near_filter_coordinate_order_is_lon_lat(modena_center):
    # GeoJSON coordinates are [longitude, latitude], not [latitude, longitude].
    filt = build_near_filter(modena_center["lat"], modena_center["lon"], radius_m=500)
    coords = filt["location"]["$near"]["$geometry"]["coordinates"]
    assert coords == [modena_center["lon"], modena_center["lat"]]


def test_build_near_filter_rejects_invalid_coordinates():
    with pytest.raises(ValueError):
        build_near_filter(200.0, 0.0, radius_m=500)


@pytest.mark.parametrize("radius_m", [0, -10])
def test_build_near_filter_rejects_non_positive_radius(modena_center, radius_m):
    with pytest.raises(ValueError):
        build_near_filter(modena_center["lat"], modena_center["lon"], radius_m=radius_m)


def test_build_near_filter_uses_custom_field_name(modena_center):
    filt = build_near_filter(modena_center["lat"], modena_center["lon"], radius_m=500, field="geo")
    assert "geo" in filt
    assert "location" not in filt


# ----------------------------------------------------------------
# build_geo_within_filter
# ----------------------------------------------------------------

def test_build_geo_within_filter_structure(sample_geojson_polygon):
    filt = build_geo_within_filter(sample_geojson_polygon)
    assert filt == {
        "location": {
            "$geoWithin": {
                "$geometry": sample_geojson_polygon
            }
        }
    }


def test_build_geo_within_filter_rejects_non_polygon_geometry(sample_geojson_point):
    with pytest.raises(ValueError):
        build_geo_within_filter(sample_geojson_point)


def test_build_geo_within_filter_rejects_missing_coordinates():
    with pytest.raises(ValueError):
        build_geo_within_filter({"type": "Polygon"})


def test_build_geo_within_filter_uses_custom_field_name(sample_geojson_polygon):
    filt = build_geo_within_filter(sample_geojson_polygon, field="geo")
    assert "geo" in filt
    assert "location" not in filt
