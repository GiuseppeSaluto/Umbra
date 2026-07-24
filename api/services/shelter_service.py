"""Climate shelter lookup by comune name."""

import re

import db.mongo as db_mongo


def find_comune(name: str) -> dict | None:
    """Case-insensitive exact match on comune name."""
    collection = db_mongo.get_collection("comuni")
    return collection.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})


def get_shelters_for_comune(name: str) -> dict:
    """Return {"comune": <comuni doc>, "shelters": [...]}. Raises ValueError if
    the comune isn't recognized - an empty shelters list is a valid, different
    outcome (comune exists, no data mapped for it yet)."""
    comune = find_comune(name)
    if comune is None:
        raise ValueError(f"'{name}' is not a recognized Italian comune")

    shelters_collection = db_mongo.get_collection("climate_shelters")
    shelters = list(shelters_collection.find({"istat_code": comune["istat_code"]}))
    return {"comune": comune, "shelters": shelters}
