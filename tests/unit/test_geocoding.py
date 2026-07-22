from unittest.mock import MagicMock, patch

from processing.geocoding import geocode

MODENA_PROVINCE = {
    "lat": "44.5384728",
    "lon": "10.9359609",
    "addresstype": "county",
    "display_name": "Modena, Emilia-Romagna, Italia",
}
MODENA_CITY = {
    "lat": "44.6458885",
    "lon": "10.9255707",
    "addresstype": "city",
    "display_name": "Modena, Emilia-Romagna, Italia",
}


def _mock_response(results):
    response = MagicMock()
    response.json.return_value = results
    response.raise_for_status.return_value = None
    return response


def test_geocode_returns_none_when_no_results():
    with patch("processing.geocoding.requests.get", return_value=_mock_response([])):
        assert geocode("nowhere") is None


def test_geocode_prefers_a_city_over_a_broader_admin_region_ranked_first():
    # Nominatim ranks by "importance", which can put a county/state ahead of the
    # city sharing its name (this happened for real with "Modena" - the province
    # outranked the city). A settlement-level result should win when one exists.
    with patch("processing.geocoding.requests.get", return_value=_mock_response([MODENA_PROVINCE, MODENA_CITY])):
        result = geocode("Modena")

    assert result["lat"] == 44.6458885
    assert result["lon"] == 10.9255707


def test_geocode_falls_back_to_first_result_when_all_are_broad_regions():
    only_broad = [MODENA_PROVINCE, {**MODENA_PROVINCE, "addresstype": "state"}]
    with patch("processing.geocoding.requests.get", return_value=_mock_response(only_broad)):
        result = geocode("Emilia-Romagna")

    assert result["lat"] == 44.5384728


def test_geocode_prefers_a_place_node_over_a_same_addresstype_boundary_centroid():
    boundary_centroid = {
        "lat": "10.0",
        "lon": "20.0",
        "class": "boundary",
        "addresstype": "city",
        "display_name": "Example, Region, Country",
    }
    place_node = {
        "lat": "10.5",
        "lon": "20.5",
        "class": "place",
        "addresstype": "city",
        "display_name": "Example, Region, Country",
    }
    with patch("processing.geocoding.requests.get", return_value=_mock_response([boundary_centroid, place_node])):
        result = geocode("Example")

    assert result["lat"] == 10.5
    assert result["lon"] == 20.5


def test_geocode_returns_display_name():
    with patch("processing.geocoding.requests.get", return_value=_mock_response([MODENA_CITY])):
        result = geocode("Modena")

    assert result["display_name"] == "Modena, Emilia-Romagna, Italia"
