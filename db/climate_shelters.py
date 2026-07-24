"""Climate shelter catalog - normalizes heterogeneous per-city open data into a
common schema and upserts it into the `climate_shelters` MongoDB collection.

Every source city publishes different fields. This class's job is to map
whatever a source provides onto the Barcelona-model criteria Umbra checks for
(docs/SPEC.md section 2: free access, shade/AC, water, seating) - a field a
source doesn't mention stays None (unknown), never guessed as False.
"""

from datetime import datetime, timezone

import db.mongo as db_mongo


class ClimateShelterCatalog:
    """Collects normalized shelter records from one or more sources, then
    upserts them into Mongo keyed by (istat_code, source_id) - two shelters can
    share a display name (e.g. two park entrances on the same street), so the
    source's own per-record ID is what has to stay unique, not the name.
    """

    def __init__(self) -> None:
        self._records: list[dict] = []

    def add(
        self,
        *,
        istat_code: str,
        source_id: str,
        comune: str,
        name: str,
        lat: float,
        lon: float,
        source_url: str,
        shelter_type: str | None = None,
        free_access: bool | None = None,
        has_air_conditioning: bool | None = None,
        shade_coverage_pct: float | None = None,
        has_drinking_water: bool | None = None,
        has_seating: bool | None = None,
        address: str | None = None,
    ) -> None:
        self._records.append(
            {
                "istat_code": istat_code,
                "source_id": source_id,
                "comune": comune,
                "name": name,
                "location": {"type": "Point", "coordinates": [lon, lat]},
                "address": address,
                "type": shelter_type,
                "free_access": free_access,
                "has_air_conditioning": has_air_conditioning,
                "shade_coverage_pct": shade_coverage_pct,
                "has_drinking_water": has_drinking_water,
                "has_seating": has_seating,
                "source_url": source_url,
                "last_verified": datetime.now(timezone.utc),
            }
        )

    def __len__(self) -> int:
        return len(self._records)

    def save(self) -> int:
        """Upsert every collected record into `climate_shelters`. Returns the
        number of records upserted."""
        collection = db_mongo.get_collection("climate_shelters")
        collection.create_index([("istat_code", 1), ("source_id", 1)], unique=True)
        for record in self._records:
            key = {"istat_code": record["istat_code"], "source_id": record["source_id"]}
            collection.update_one(key, {"$set": record}, upsert=True)
        return len(self._records)
