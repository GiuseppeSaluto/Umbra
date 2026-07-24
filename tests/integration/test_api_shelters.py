from unittest.mock import MagicMock, patch

SAMPLE_COMUNE = {
    "istat_code": "048017",
    "name": "Firenze",
    "province": "Firenze",
    "province_abbr": "FI",
    "region": "Toscana",
}

SAMPLE_SHELTER = {
    "istat_code": "048017",
    "source_id": "biblioteche:1",
    "name": "Biblioteca delle Oblate",
    "type": "library",
    "free_access": True,
}


def _patched_collections(comuni_result, shelters_result=None):
    comuni_collection = MagicMock()
    comuni_collection.find_one.return_value = comuni_result
    shelters_collection = MagicMock()
    shelters_collection.find.return_value = shelters_result or []

    def get_collection(name):
        return {"comuni": comuni_collection, "climate_shelters": shelters_collection}[name]

    return patch("db.mongo.get_collection", side_effect=get_collection)


def test_shelters_endpoint_returns_shelters_for_known_comune(app):
    with _patched_collections(SAMPLE_COMUNE, [SAMPLE_SHELTER]):
        response = app.test_client().get("/api/shelters", query_string={"comune": "Firenze"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["comune"] == "Firenze"
    assert data["shelter_count"] == 1
    assert data["shelters"][0]["name"] == "Biblioteca delle Oblate"
    assert "istat_code" not in data["shelters"][0]


def test_shelters_endpoint_200_with_empty_list_for_comune_with_no_data(app):
    with _patched_collections(SAMPLE_COMUNE, []):
        response = app.test_client().get("/api/shelters", query_string={"comune": "Modena"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["shelter_count"] == 0
    assert data["shelters"] == []


def test_shelters_endpoint_404_for_unknown_comune(app):
    with _patched_collections(None):
        response = app.test_client().get("/api/shelters", query_string={"comune": "Nonexistentville"})

    assert response.status_code == 404


def test_shelters_endpoint_400_when_comune_missing(app):
    response = app.test_client().get("/api/shelters")
    assert response.status_code == 400
