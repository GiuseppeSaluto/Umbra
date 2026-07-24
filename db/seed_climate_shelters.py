"""One-time seed: loads real climate shelter data into MongoDB.

Only Firenze is wired up - the only comune with a verified structured open-data
source (checked 2026-07-24; Milano/Bologna/Torino have press coverage but no
downloadable dataset). Add more comuni here once they publish one.

Usage: python -m db.seed_climate_shelters
"""

import os

import requests
from pyproj import Transformer

from db.climate_shelters import ClimateShelterCatalog

FIRENZE_ISTAT_CODE = "048017"
FIRENZE_AREE_FRESCHE_URL = "https://datigis.comune.fi.it/json/rifugi_climatici_aree_fresche.json"
FIRENZE_BIBLIOTECHE_URL = "https://datigis.comune.fi.it/json/rifugi_climatici_biblioteche.json"
FIRENZE_SOURCE_PAGE = "https://opendata.comune.fi.it/content/rifugi-climatici"

REQUEST_TIMEOUT_S = 15

_epsg3003_to_wgs84 = Transformer.from_crs("EPSG:3003", "EPSG:4326", always_xy=True)


def _polygon_centroid(coordinates: list) -> tuple[float, float]:
    """Average of a MultiPolygon's first ring - good enough for a marker, not area math."""
    ring = coordinates[0][0]
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return sum(lons) / len(lons), sum(lats) / len(lats)


def _add_aree_fresche(catalog: ClimateShelterCatalog) -> None:
    response = requests.get(FIRENZE_AREE_FRESCHE_URL, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()

    for feature in response.json()["features"]:
        props = feature["properties"]
        lon, lat = _polygon_centroid(feature["geometry"]["coordinates"])
        descrizione = props["descrizione"]

        catalog.add(
            istat_code=FIRENZE_ISTAT_CODE,
            source_id=f"aree_fresche:{props['cod_area']}",
            comune="Firenze",
            name=props["nome_area"],
            lat=lat,
            lon=lon,
            source_url=FIRENZE_SOURCE_PAGE,
            shelter_type="giardino" if "giardino" in descrizione else "parco",
            free_access=True,
            shade_coverage_pct=props["percentuale_ombreggi"],
            has_drinking_water=True,
            has_seating="arredi" in descrizione,
            address=props["ingresso"],
        )


def _add_biblioteche(catalog: ClimateShelterCatalog) -> None:
    response = requests.get(FIRENZE_BIBLIOTECHE_URL, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()

    for feature in response.json()["features"]:
        props = feature["properties"]
        x, y = feature["geometry"]["coordinates"]
        lon, lat = _epsg3003_to_wgs84.transform(x, y)
        address = f"{props['indirizzo']}, {props['civico']}" if props.get("civico") else props["indirizzo"]

        catalog.add(
            istat_code=FIRENZE_ISTAT_CODE,
            source_id=f"biblioteche:{props['id']}",
            comune="Firenze",
            name=props["nome"],
            lat=lat,
            lon=lon,
            source_url=FIRENZE_SOURCE_PAGE,
            shelter_type="library",
            free_access=True,
            has_air_conditioning=True,
            has_seating=True,
            address=address,
        )


def seed_firenze() -> int:
    catalog = ClimateShelterCatalog()
    _add_aree_fresche(catalog)
    _add_biblioteche(catalog)
    return catalog.save()


if __name__ == "__main__":
    from dotenv import load_dotenv

    import db.mongo as db_mongo

    load_dotenv(os.path.expanduser("~/.secrets/umbra"))
    load_dotenv(".env")

    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_mongo.get_client(mongo_uri)

    total = seed_firenze()
    print(f"Upserted {total} climate shelters into MongoDB.")
