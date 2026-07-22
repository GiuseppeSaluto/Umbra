from api.services.map_service import get_area_map_html

# ----------------------------------------------------------------
# api/services/map_service.py
# ----------------------------------------------------------------


def test_get_area_map_html_returns_html_document(mock_mongo, mock_sentinel, modena_center):
    html = get_area_map_html(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert "<html" in html.lower()


def test_get_area_map_html_embeds_center_coordinates(mock_mongo, mock_sentinel, modena_center):
    html = get_area_map_html(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert str(modena_center["lat"]) in html
    assert str(modena_center["lon"]) in html


# ----------------------------------------------------------------
# GET /map
# ----------------------------------------------------------------


def test_map_endpoint_returns_200_html(client, modena_center):
    response = client.get(
        "/map", query_string={"lat": modena_center["lat"], "lon": modena_center["lon"], "radius_m": 500}
    )
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b"leaflet" in response.data.lower()


def test_map_endpoint_uses_default_radius_when_omitted(client, modena_center):
    response = client.get("/map", query_string={"lat": modena_center["lat"], "lon": modena_center["lon"]})
    assert response.status_code == 200


def test_map_endpoint_400_on_missing_lat(client, modena_center):
    response = client.get("/map", query_string={"lon": modena_center["lon"]})
    assert response.status_code == 400


def test_map_endpoint_400_on_non_numeric_lat(client, modena_center):
    response = client.get("/map", query_string={"lat": "not-a-number", "lon": modena_center["lon"]})
    assert response.status_code == 400


def test_map_endpoint_400_on_non_positive_radius(client, modena_center):
    response = client.get(
        "/map",
        query_string={"lat": modena_center["lat"], "lon": modena_center["lon"], "radius_m": -10},
    )
    assert response.status_code == 400
