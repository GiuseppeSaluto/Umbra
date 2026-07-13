# Umbra 🌳

[![CI](https://github.com/GiuseppeSaluto/Umbra/actions/workflows/ci.yml/badge.svg)](https://github.com/GiuseppeSaluto/Umbra/actions/workflows/ci.yml)

Geospatial platform that uses real satellite data (Sentinel-2) to objectively identify
urban heat islands and green areas, surfacing climate refuges on a navigable map.
Built to close a gap in Italian municipal planning: there is no national standard for
mapping climate refuges — every city does it independently, if at all.

---

## Architecture

```
Copernicus API (Sentinel-2)
      │
      ▼
┌───────────────────────────────────┐
│  Python processing (rasterio)      │  ← NDVI / LST computation
│   processing/sentinel, ndvi, heat  │
└────────────┬───────────────────────┘
             │  persist
             ▼
┌───────────────────────────────────┐
│  MongoDB (2dsphere index)          │
│   green areas · heat islands       │
│   climate shelters                 │
└────────────┬───────────────────────┘
             │  query
             ▼
┌───────────────────────────────────┐
│  Flask REST API                    │  ← orchestration, serves the map
│   api/routes · api/services        │
└────────────┬───────────────────────┘
             │  render
             ▼
┌───────────────────────────────────┐
│  Folium map (Leaflet HTML)         │
│   served on /map                   │
└───────────────────────────────────┘
```

In Phase 2, a Rust microservice (Axum) takes over raster processing for
performance. In Phase 3, Valkey caches frequent geospatial queries. Neither is part
of the MVP — see [Roadmap](#roadmap).

---

## Status

Early stage — repository skeleton and test contracts only, no feature implemented yet.
The project follows a test-first workflow: fixtures and contracts in `tests/conftest.py`
are defined before the implementation exists. Full specification: [docs/SPEC.md](docs/SPEC.md).

---

## Quick Start (local dev)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

# Real secrets never go in .env - create a separate file outside the repo:
mkdir -p ~/.secrets && cat > ~/.secrets/umbra <<'EOF'
COPERNICUS_CLIENT_ID=...
COPERNICUS_CLIENT_SECRET=...
FLASK_SECRET_KEY=...
EOF
chmod 600 ~/.secrets/umbra

pytest
```

MongoDB is expected locally on the default port:

```bash
mongod --dbpath /path/to/data --logpath /path/to/mongo.log --fork
```

Umbra connects to its own database (`umbra`, hardcoded in `db/mongo.py`) on the shared
local MongoDB instance — it does not read or write any other project's database. On first
connection it creates whatever collections and 2dsphere indexes are missing, so the schema
is self-consistent from a clean instance.

---

## Project Structure

```
umbra/
├── api/
│   ├── routes/              # Flask endpoints
│   ├── services/            # Isolated business logic — key architectural boundary
│   ├── models/               # Domain models (Pydantic)
│   └── app.py
├── processing/
│   ├── sentinel.py          # Copernicus data download and access
│   ├── ndvi.py               # NDVI computation from Sentinel-2 bands
│   └── heat.py               # LST / heat island computation
├── rust_engine/              # Rust microservice (Axum) — activated in Phase 2
├── db/
│   ├── mongo.py              # MongoDB connection and queries
│   └── valkey_cache.py       # Valkey cache layer (Phase 3)
├── map/
│   └── renderer.py           # Folium map generation — HTML output on /map
├── docs/
│   └── SPEC.md                # Full project specification
├── tests/
│   ├── unit/                 # Pure computation logic (NDVI, LST, geo)
│   ├── integration/           # Flask + MongoDB, services mocked
│   ├── contract/              # Boundaries between components
│   └── conftest.py            # Shared fixtures — no real service is contacted
├── .env.example
└── requirements.txt
```

---

## Environment Variables

Config is split across two files, loaded in this order by `api/app.py`:

| Variable | Required | Description |
|---|---|---|
| `COPERNICUS_CLIENT_ID` | Yes | Copernicus Data Space Ecosystem / Sentinel Hub OAuth client ID |
| `COPERNICUS_CLIENT_SECRET` | Yes | Copernicus Data Space Ecosystem / Sentinel Hub OAuth client secret |
| `FLASK_SECRET_KEY` | Yes | Secret key for Flask session/cookie signing — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |

**`.env`** (project root, git-ignored, copied from `.env.example`) — non-sensitive config only:

| Variable | Required | Description |
|---|---|---|
| `MONGO_URI` | No | MongoDB connection string, host only — database name is `umbra`, set in code (default: `mongodb://localhost:27017`) |
| `VALKEY_URL` | No | Valkey connection string — used from Phase 3 onward |
| `RUST_ENGINE_URL` | No | Rust engine base URL — used from Phase 2 onward |
| `FLASK_ENV` | No | `development` or `production` |

---

## Testing

```bash
pytest
```

Three levels, all defined in `tests/`:

- **Unit** — pure functions, zero external dependencies (NDVI range, LST consistency).
- **Integration** — Flask + MongoDB together, with services mocked.
- **Contract** — verifies the data format handed between `processing/` and `api/services/`.

No real external service (Copernicus, MongoDB, Valkey) is ever contacted during tests —
everything is mocked via fixtures in `tests/conftest.py`. See `docs/SPEC.md` §11 for the
full testing philosophy.

---

## Roadmap

| Phase | Goal |
|---|---|
| 1 — MVP | Sentinel-2 pipeline → heat island map + green areas for a geographic area |
| 2 — Rust Engine | Replace Python raster processing with a Rust microservice |
| 3 — Cache | Add Valkey to cache results for already-processed areas |
| 4 — Expansions | Heat wave alerting, multi-city coverage, map UX improvements |
