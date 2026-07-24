from unittest.mock import MagicMock, patch

import pytest

from api.services.shelter_service import find_comune, get_shelters_for_comune

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
}


def _mock_collections(comuni_result, shelters_result=None):
    comuni_collection = MagicMock()
    comuni_collection.find_one.return_value = comuni_result
    shelters_collection = MagicMock()
    shelters_collection.find.return_value = shelters_result or []

    def get_collection(name):
        return {"comuni": comuni_collection, "climate_shelters": shelters_collection}[name]

    return get_collection


def test_find_comune_queries_case_insensitively():
    get_collection = _mock_collections(SAMPLE_COMUNE)
    with patch("db.mongo.get_collection", side_effect=get_collection):
        result = find_comune("firenze")

    assert result == SAMPLE_COMUNE


def test_find_comune_returns_none_when_not_found():
    get_collection = _mock_collections(None)
    with patch("db.mongo.get_collection", side_effect=get_collection):
        result = find_comune("Nonexistentville")

    assert result is None


def test_get_shelters_for_comune_raises_for_unknown_comune():
    get_collection = _mock_collections(None)
    with patch("db.mongo.get_collection", side_effect=get_collection):
        with pytest.raises(ValueError):
            get_shelters_for_comune("Nonexistentville")


def test_get_shelters_for_comune_returns_empty_list_when_comune_has_no_data():
    get_collection = _mock_collections(SAMPLE_COMUNE, shelters_result=[])
    with patch("db.mongo.get_collection", side_effect=get_collection):
        result = get_shelters_for_comune("Modena")

    assert result["comune"] == SAMPLE_COMUNE
    assert result["shelters"] == []


def test_get_shelters_for_comune_returns_matching_shelters():
    get_collection = _mock_collections(SAMPLE_COMUNE, shelters_result=[SAMPLE_SHELTER])
    with patch("db.mongo.get_collection", side_effect=get_collection):
        result = get_shelters_for_comune("Firenze")

    assert result["shelters"] == [SAMPLE_SHELTER]
