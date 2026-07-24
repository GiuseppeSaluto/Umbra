"""One-time seed: loads ISTAT's official comuni list into MongoDB.

Source: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
(latin-1 encoded, semicolon-delimited, snapshotted at data/istat_comuni.csv - ISTAT
updates this a few times a year, not something to re-fetch on every app start).

Coordinates are deliberately not stored here - a comune is geocoded on demand via
processing/geocoding.py, the same path already used for "Search a place". This list's
job is just to validate/autocomplete comune names and give climate_shelters a stable
key (istat_code) to attach to, instead of a free-text name.

Not part of db/mongo.py's automatic bootstrap - run manually after a fresh Mongo setup:
    python -m db.seed_comuni
"""

import csv
import os

from dotenv import load_dotenv

import db.mongo as db_mongo

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "istat_comuni.csv")

_ISTAT_CODE_COL = 4
_NAME_COL = 6
_REGION_COL = 10
_PROVINCE_COL = 11
_PROVINCE_ABBR_COL = 14


def _parse_row(row: list[str]) -> dict:
    return {
        "istat_code": row[_ISTAT_CODE_COL],
        "name": row[_NAME_COL],
        "province": row[_PROVINCE_COL],
        "province_abbr": row[_PROVINCE_ABBR_COL],
        "region": row[_REGION_COL],
    }


def load_comuni(csv_path: str = DEFAULT_CSV_PATH) -> int:
    """Upsert every comune from the ISTAT CSV into the `comuni` collection, keyed
    by istat_code. Returns the number of comuni upserted."""
    collection = db_mongo.get_collection("comuni")
    collection.create_index("istat_code", unique=True)

    with open(csv_path, encoding="latin-1", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # header

        count = 0
        for row in reader:
            doc = _parse_row(row)
            collection.update_one({"istat_code": doc["istat_code"]}, {"$set": doc}, upsert=True)
            count += 1
    return count


if __name__ == "__main__":
    load_dotenv(os.path.expanduser("~/.secrets/umbra"))
    load_dotenv(".env")

    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_mongo.get_client(mongo_uri)

    total = load_comuni()
    print(f"Upserted {total} comuni into MongoDB.")
