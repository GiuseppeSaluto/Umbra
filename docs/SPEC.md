# Umbra — Project Specification

**Geospatial Climate Refuge Platform**
Giuseppe Saluto · 2026

---

## 1. Problem and motivation

Heat waves are becoming more frequent in Italy and Europe. Cities can be up to 4°C hotter than the surrounding rural areas due to the urban heat island effect: asphalt and concrete absorb heat during the day and release it at night. Italy has no national regulatory framework for climate refuges — each municipality maps its own cool spaces independently, with no shared standard and no unified platform.

Umbra exists to close this gap with a technical tool: a web platform that uses real satellite data (Sentinel-2) to objectively identify heat islands and green areas, giving the user a navigable map of their geographic area.

---

## 2. Definition — Climate refuge

A public space with free, open access that offers relief from extreme temperatures while keeping its normal function (library, park, museum, civic center). It is not an emergency room, nor a shelter for the homeless.

**Technical criteria (Barcelona model):**

- Free access, no purchase or consumption required
- Open spaces: shade coverage above 70% of the surface
- Indoor spaces: working air conditioning, stable temperature of 26°C in summer
- Availability of drinking water and seating
- Not intended for people who need medical care

---

## 3. Technology stack

> Guiding principle: open source tools only. No vendor lock-in, no proprietary licenses.

| Component | Technology | Role |
|---|---|---|
| Backend API | Python 3.12 + Flask (async views) | Orchestration, REST endpoints, serves the map |
| Raster processing | Python (numpy) | NDVI / LST computation on Sentinel-2/3 imagery |
| Primary database | MongoDB + 2dsphere index | Storage for GeoJSON, green areas, heat islands, refuges, query cache |
| Visual layer | Folium (Python) | Generates a Leaflet map from Python, served by Flask as HTML |
| Satellite data | Sentinel-2 / Sentinel-3 via Copernicus API | NDVI (vegetation), LST approximation (surface temperature) |

## 4. MongoDB — Primary database

MongoDB is Umbra's primary database. The choice is not about technical familiarity but about fitness for the problem: geospatial data is natively represented as GeoJSON, which is MongoDB's document format. Refuges, green areas and heat islands are GeoJSON geometries (Point, Polygon) — storing them in MongoDB means zero conversions and zero ORM mapping.

**Why not a relational DB:**
The project's core geospatial queries — "find refuges within 500m", "which green areas are contained in this area" — require specific extensions in a relational DB (PostGIS on PostgreSQL). MongoDB handles them natively with the 2dsphere index, with no extra dependencies.

**2dsphere index — how it works:**

- Interprets coordinates as points on a sphere (Earth's surface, curvature included) rather than as generic numbers on a plane.
- Builds a tree structure based on geohashing that immediately narrows the search to the relevant geographic zone — no full collection scan.
- Documents must expose a GeoJSON field with `type` and `coordinates`:
  ```json
  {
    "location": {
      "type": "Point",
      "coordinates": [10.92, 44.63]
    }
  }
  ```
- Enabled queries: `$near` (nearest points ordered by distance), `$geoWithin` (points inside a polygon, e.g. municipal boundaries), `$geoIntersects` (intersection between geometries).
- Supports both `Point` (a single refuge, a drinking fountain) and `Polygon` (green area, heat island as a delimited zone).

---

## 5. Satellite data — Sentinel-2 / Copernicus

**NDVI (Normalized Difference Vegetation Index):**
Computed from Sentinel-2 bands B4 (red) and B8 (near infrared). Values range from -1 to +1: above 0.3 indicates dense vegetation, below 0 indicates impermeable surfaces (asphalt, buildings). Identifies green areas.

```
NDVI = (B8 - B4) / (B8 + B4)
```

**LST (Land Surface Temperature):**
Sentinel-2 has no thermal band, so LST is approximated from Sentinel-3 SLSTR's S9 thermal channel (brightness temperature, ~1km resolution) - a defensible proxy for relative hot/cool comparison at neighborhood scale, not atmospherically-corrected split-window LST. Identifies urban heat islands — the hottest zones of the city.

**Access:**
Copernicus Data Space Ecosystem (CDSE) — free, registration required. Python SDK: `sentinelhub`, which handles OAuth2 authentication and returns band data directly as numpy arrays.

**Format and libraries:**
`sentinelhub`'s Process API returns numpy arrays directly - no local GeoTIFF handling needed. `numpy` for pixel-by-pixel computation.

**Resolution:**
10m per pixel for optical bands — enough to distinguish parks, streets and city blocks in an urban context.

---

## 6. Test suite

### Philosophy

Tests do not verify code after the fact — they define the contract before the code exists. The implementation's job is to make the test pass. Output with no test behind it is not a feature: it's an opinion with semicolons.

The verification command is single: `pytest`. Green = shipped. Red = not done.

### Three levels

**Unit tests** (`tests/unit/`) — pure functions, zero external dependencies, instant execution. They test computation logic: NDVI in range, LST consistency, division by zero handled. These are the first to be written, before the code.

**Integration tests** (`tests/integration/`) — Flask + MongoDB together, with services mocked. They test HTTP endpoints: status code, GeoJSON response schema, search radius compliance, coordinate validation.

**Contract tests** (`tests/contract/`) — verify the boundaries between components. If `processing/` returns a format that `api/services/` doesn't expect, the contract test goes red regardless of how correct each piece of code is on its own.

### conftest.py — shared fixtures

Centralizes all mocks and synthetic data shared across test levels. No real service is contacted during tests.

### Critical rule

Every assertion must check the data, not the container. `assert response.status_code == 200` is not a test — it's theater. The test must check that the GeoJSON contains features within the requested radius, that NDVI is within the physically possible range, that the MongoDB document respects the 2dsphere schema. If the directive is vague, the suite is theater and wrong output passes green.

---

*Umbra — SPEC.md v1.2 · Giuseppe Saluto · July 2026*
