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
| Backend API | Python 3.12 + Flask | Orchestration, REST endpoints, serves the map |
| Computation Engine | Rust + Axum | Raster NDVI / LST processing on Sentinel-2 imagery |
| Primary database | MongoDB + 2dsphere index | Storage for GeoJSON, green areas, heat islands, refuges |
| Cache | Valkey | Cache for frequent geospatial queries (open source, Linux Foundation) |
| Visual layer | Folium (Python) | Generates a Leaflet map from Python, served by Flask as HTML |
| Satellite data | Sentinel-2 / Sentinel-3 via Copernicus API | NDVI (vegetation), LST approximation (surface temperature) |

**Notes:**
- Docker is not used during active development. It will be introduced once the project is functional, as the final deployment layer.
- Rust is not forced into the MVP. It comes in only once there is a measured bottleneck to replace.

---

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

**Why not PostGIS:**
PostGIS is the standard for advanced GIS work — operations on complex geometries, area calculations, buffers, polygon unions, native raster support. For Umbra, where raster data (Sentinel-2 GeoTIFF) is processed separately by Python/Rust and the results are saved as documents, MongoDB covers all the necessary use cases. PostGIS would become relevant only if we wanted to query raster data directly from the database — an architectural choice Umbra does not make.

---

## 5. Valkey — Cache layer

Valkey is the open source fork of Redis, created in 2024 by the Linux Foundation after Redis Ltd changed its license from BSD to SSPL (no longer open source). It is API-compatible with Redis: no application code changes are needed to adopt it. Choosing Valkey over Redis is a project principle — genuinely open source tools only.

**Role in Umbra:**

- Valkey keeps all data in RAM — reads are orders of magnitude faster than a MongoDB query, even with a geospatial index.
- Caches frequent geospatial queries: if many users search the same area (e.g. downtown Modena), the result is served from Valkey for N minutes without re-running the MongoDB query.
- Configurable TTL (Time To Live) per data type: NDVI/LST data changes with new Sentinel-2 imagery (days), refuge data changes rarely (hours/days).
- Key-value data model: simple, not suited to complex queries — it does not replace MongoDB, it only sits alongside it as a response cache.
- Introduced in Phase 3, not in the MVP: bottlenecks are measured first, then cached.

---

## 6. Architecture and data flow

```
Copernicus API (sentinelhub)  ->  Python processing (numpy)  ->  MongoDB
                                   |
             Flask REST API  <-  Valkey (cache)
                   |
         Folium (generates HTML map)  ->  User's browser
```

In Phase 2 the "Python processing" block is joined or replaced by the Rust microservice (Axum, port 8080), called by Flask over HTTP. The boundary is clean: Flask does not know, and does not need to know, whether the computation is done by Python or Rust — it only receives the result.

---

## 7. Repository structure

```
umbra/
|-- api/
|   |-- routes/              # Flask endpoints
|   |-- services/            # Isolated business logic - key architectural boundary
|   |-- models/              # Domain models
|   `-- app.py
|-- processing/
|   |-- sentinel.py          # Copernicus data download and access
|   |-- ndvi.py              # NDVI computation from Sentinel-2 bands
|   `-- heat.py              # LST / heat island computation
|-- rust_engine/             # Rust microservice (Axum) - activated in Phase 2
|   |-- src/
|   |   |-- domain/
|   |   |-- logic/
|   |   |-- dto/
|   |   `-- api/
|   `-- Cargo.toml
|-- db/
|   |-- mongo.py             # MongoDB connection and queries
|   `-- valkey_cache.py      # Valkey cache layer
|-- map/
|   `-- renderer.py          # Folium map generation - HTML output on /map
|-- docs/
|   `-- SPEC.md              # This file
|-- .env.example             # Copernicus API key, connection strings - never committed
|-- .gitignore
`-- requirements.txt
```

**Note on `api/services/`:** this is the key architectural boundary. Flask calls the services, the services call processing/ or rust_engine/. When Rust comes in, it replaces a call inside services/ without touching the rest.

---

## 8. Satellite data — Sentinel-2 / Copernicus

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
`sentinelhub`'s Process API returns numpy arrays directly - no local GeoTIFF handling needed. `numpy` for pixel-by-pixel computation. Rust in Phase 2 will handle this processing for performance on large images.

**Resolution:**
10m per pixel for optical bands — enough to distinguish parks, streets and city blocks in an urban context.

---

## 9. Development roadmap

| Phase | Goal | Components involved |
|---|---|---|
| 1 — MVP | Sentinel-2 pipeline -> heat island map + green areas per geographic area | Flask, MongoDB, Folium, Copernicus API (sentinelhub), numpy |
| 2 — Rust Engine | Replace Python raster processing with a Rust microservice for performance on large images | Rust + Axum, called by Flask over internal HTTP |
| 3 — Cache | Add Valkey to cache results for already-processed areas (variable TTL for satellite data) | Valkey, cache layer in db/valkey_cache.py |
| 4 — Expansions | Heat wave alerting (Open-Meteo API), multi-city coverage, map UX improvements | Open-Meteo, historical Sentinel-2 data, potential PWA |

---

## 10. Explicit limits and architectural decisions

- **No scraping:** dropped in favor of structured satellite data via API. Scraping municipal websites is fragile, not standardizable, not scalable.
- **No Docker in development:** introduced only once the project is functional, as a deployment layer.
- **Rust not forced in the MVP:** the raster pipeline is initially all Python. Rust comes in only once there is a measured bottleneck — not before.
- **Open source only:** Valkey (no proprietary Redis), MongoDB Community, Sentinel-2/Copernicus (public EU data), Flask, Axum, Folium.
- **Narrow MVP scope:** v1 does exactly one thing — takes the user's location, downloads Sentinel-2 data for that area, returns a map with LST and NDVI. No institutional refuges, no weather alerting, no cache in v1.

---

## 11. Test suite

### Philosophy

Tests do not verify code after the fact — they define the contract before the code exists. The implementation's job is to make the test pass. Output with no test behind it is not a feature: it's an opinion with semicolons.

The verification command is single: `pytest`. Green = shipped. Red = not done.

### Three levels

**Unit tests** (`tests/unit/`) — pure functions, zero external dependencies, instant execution. They test computation logic: NDVI in range, LST consistency, division by zero handled. These are the first to be written, before the code.

**Integration tests** (`tests/integration/`) — Flask + MongoDB together, with services mocked. They test HTTP endpoints: status code, GeoJSON response schema, search radius compliance, coordinate validation.

**Contract tests** (`tests/contract/`) — verify the boundaries between components. If `processing/` returns a format that `api/services/` doesn't expect, the contract test goes red regardless of how correct each piece of code is on its own. Critical in an AI-generated project where components are written separately.

### Structure

```
tests/
|-- unit/
|   |-- test_ndvi.py
|   |-- test_heat.py
|   `-- test_geo.py
|-- integration/
|   |-- test_api_spots.py
|   |-- test_api_map.py
|   `-- test_mongo_queries.py
|-- contract/
|   |-- test_processing_contract.py
|   `-- test_api_folium_contract.py
|-- conftest.py
`-- fixtures/
    `-- sample_geotiff/
```

### conftest.py — shared fixtures

Centralizes all mocks and synthetic data shared across test levels. No real service is contacted during tests.

**Available fixtures:**

- `sample_b4`, `sample_b8` — synthetic Sentinel-2 bands (10x10 numpy arrays)
- `sample_lst` — synthetic Land Surface Temperature with hot zones (~42°C) and green zones (~28°C)
- `sample_ndvi_array` — NDVI precomputed from the synthetic samples
- `sample_sentinel_response` — full simulated response from `fetch_area_data()`
- `mock_mongo_collection` — mocked MongoDB collection with sample GeoJSON data
- `mock_mongo` — full PyMongo patch for integration tests
- `mock_valkey` — mocked Valkey client with a cache miss by default
- `mock_valkey_hit` — Valkey with a cache hit to test the cache path
- `mock_sentinel` — patch of `fetch_area_data()` with no real calls to Copernicus
- `client` — Flask test client with all services mocked
- `modena_center` — reference geographic coordinates for tests
- `sample_geojson_point`, `sample_geojson_polygon` — valid GeoJSON geometries for schema tests

### Critical rule

Every assertion must check the data, not the container. `assert response.status_code == 200` is not a test — it's theater. The test must check that the GeoJSON contains features within the requested radius, that NDVI is within the physically possible range, that the MongoDB document respects the 2dsphere schema. If the directive is vague, the suite is theater and wrong output passes green.

---

## 12. Reference architectural pattern — AstroForge

Umbra replicates and adapts the pattern already validated in AstroForge (`github.com/GiuseppeSaluto/AstroForge`):

- Flask orchestrates
- Rust computes (separate microservice over HTTP)
- MongoDB persists
- Python-only visual layer (Textual there, Folium here)

The difference is the domain: geospatial/satellite data instead of NASA/asteroid data. AstroForge's `services/`, `infra/`, `docs/` structure is the starting template.

---

*Umbra — SPEC.md v1.1 · Giuseppe Saluto · July 2026*
