def test_index_returns_200_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_index_contains_a_single_geolocation_call(client):
    html = client.get("/").get_data(as_text=True)
    assert html.count("navigator.geolocation.getCurrentPosition") == 1


def test_index_redirects_to_map_endpoint_with_coordinates(client):
    html = client.get("/").get_data(as_text=True)
    assert "/map?lat=" in html
    assert "position.coords.latitude" in html
    assert "position.coords.longitude" in html


def test_index_has_manual_fallback_form_for_denied_geolocation(client):
    html = client.get("/").get_data(as_text=True)
    assert 'action="/map"' in html
    assert 'name="lat"' in html
    assert 'name="lon"' in html
    assert 'name="radius_m"' in html


def test_index_splits_pasted_lat_lon_pair_into_both_fields(client):
    html = client.get("/").get_data(as_text=True)
    assert "splitPastedCoordinates" in html
    assert 'getElementById("lat-input")' in html
    assert 'getElementById("lon-input")' in html
