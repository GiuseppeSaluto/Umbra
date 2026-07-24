from unittest.mock import MagicMock, patch

import pytest

from db.climate_shelters import ClimateShelterCatalog
from db.seed_climate_shelters import _add_aree_fresche, _add_biblioteche, seed_firenze

SAMPLE_AREA_WITH_ARREDI = {
    "type": "Feature",
    "properties": {
        "id": 1,
        "cod_area": "00100",
        "nome_area": "Parco di viale dei Tanini",
        "percentuale_ombreggi": 73,
        "ingresso": "Viale dei Tanini, 20",
        "descrizione": "Area verde classificata come parco, caratterizzata da ombreggiatura "
        "maggiore del 70% e dalla presenza di uno o più fontanelli e arredi.",
    },
    "geometry": {
        "type": "MultiPolygon",
        "coordinates": [[[[11.20, 43.70], [11.22, 43.70], [11.22, 43.72], [11.20, 43.72], [11.20, 43.70]]]],
    },
}

SAMPLE_GARDEN_NO_ARREDI = {
    "type": "Feature",
    "properties": {
        "id": 2,
        "cod_area": "00200",
        "nome_area": "Giardino di Via Roma",
        "percentuale_ombreggi": 80,
        "ingresso": "Via Roma, 1",
        "descrizione": "Area verde classificata come giardino, caratterizzata da ombreggiatura "
        "maggiore del 70% e dalla presenza di uno o più fontanelli.",
    },
    "geometry": {
        "type": "MultiPolygon",
        "coordinates": [[[[11.30, 43.80], [11.32, 43.80], [11.32, 43.82], [11.30, 43.82], [11.30, 43.80]]]],
    },
}

SAMPLE_BIBLIOTECA = {
    "type": "Feature",
    "properties": {
        "id": 1,
        "nome": "Biblioteca delle Oblate",
        "indirizzo": "Via dell'Oriuolo",
        "civico": "24",
        "telefono": "055 2616512",
        "mail": "bibliotecadelleoblate@comune.fi.it",
        "orario": "https://cultura.comune.fi.it/pagina/orari-e-contatti",
        "note": None,
    },
    "geometry": {"type": "Point", "coordinates": [1681921.63092, 4849074.13289]},
}


def _fake_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_add_aree_fresche_reads_shade_pct_and_water_directly():
    catalog = ClimateShelterCatalog()
    with patch(
        "db.seed_climate_shelters.requests.get",
        return_value=_fake_response({"features": [SAMPLE_AREA_WITH_ARREDI]}),
    ):
        _add_aree_fresche(catalog)

    record = catalog._records[0]
    assert record["name"] == "Parco di viale dei Tanini"
    assert record["shade_coverage_pct"] == 73
    assert record["has_drinking_water"] is True
    assert record["type"] == "parco"


def test_add_aree_fresche_only_flags_seating_when_arredi_is_mentioned():
    catalog = ClimateShelterCatalog()
    with patch(
        "db.seed_climate_shelters.requests.get",
        return_value=_fake_response({"features": [SAMPLE_AREA_WITH_ARREDI, SAMPLE_GARDEN_NO_ARREDI]}),
    ):
        _add_aree_fresche(catalog)

    assert catalog._records[0]["has_seating"] is True
    assert catalog._records[1]["has_seating"] is False
    assert catalog._records[1]["type"] == "giardino"


def test_add_aree_fresche_computes_a_centroid_inside_the_polygon():
    catalog = ClimateShelterCatalog()
    with patch(
        "db.seed_climate_shelters.requests.get",
        return_value=_fake_response({"features": [SAMPLE_AREA_WITH_ARREDI]}),
    ):
        _add_aree_fresche(catalog)

    lon, lat = catalog._records[0]["location"]["coordinates"]
    assert 11.20 <= lon <= 11.22
    assert 43.70 <= lat <= 43.72


def test_add_biblioteche_reprojects_epsg3003_to_wgs84():
    catalog = ClimateShelterCatalog()
    with patch(
        "db.seed_climate_shelters.requests.get",
        return_value=_fake_response({"features": [SAMPLE_BIBLIOTECA]}),
    ):
        _add_biblioteche(catalog)

    record = catalog._records[0]
    lon, lat = record["location"]["coordinates"]
    assert lon == pytest.approx(11.260049, abs=1e-4)
    assert lat == pytest.approx(43.772234, abs=1e-4)
    assert record["has_air_conditioning"] is True
    assert record["address"] == "Via dell'Oriuolo, 24"


def test_seed_firenze_saves_records_from_both_sources(mock_mongo):
    with patch(
        "db.seed_climate_shelters.requests.get",
        side_effect=[
            _fake_response({"features": [SAMPLE_AREA_WITH_ARREDI]}),
            _fake_response({"features": [SAMPLE_BIBLIOTECA]}),
        ],
    ):
        count = seed_firenze()

    assert count == 2
    assert mock_mongo.update_one.call_count == 2
