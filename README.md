# Umbra 🌳

[![CI](https://github.com/GiuseppeSaluto/Umbra/actions/workflows/ci.yml/badge.svg)](https://github.com/GiuseppeSaluto/Umbra/actions/workflows/ci.yml)

Geospatial platform that uses real satellite data (Sentinel-2) to objectively identify
urban heat islands and green areas, surfacing climate refuges on a navigable map.
Built to close a gap in Italian municipal planning: there is no national standard for
mapping climate refuges — every city does it independently, if at all.

---

## Architecture

```
Copernicus API (Sentinel-2 + Sentinel-3)
      │
      ▼
┌───────────────────────────────────┐
│  Python processing (sentinelhub)   │  ← NDVI / LST computation
│   processing/sentinel, ndvi, heat  │
└────────────┬───────────────────────┘
             │  persist
             ▼
┌───────────────────────────────────┐
│  MongoDB (2dsphere index)          │
│   area_analyses (query cache)      │
│   green areas · heat islands       │
│   climate shelters (not yet - see  │
│     Status below)                  │
└────────────┬───────────────────────┘
             │  query
             ▼
┌───────────────────────────────────┐
│  Flask REST API (async views)      │  ← orchestration, serves the map
│   api/routes · api/services        │
└────────────┬───────────────────────┘
             │  render
             ▼
┌───────────────────────────────────┐
│  Folium map (Leaflet HTML)         │
│   served on /map                   │
└───────────────────────────────────┘
```

Query results are cached in MongoDB's own `area_analyses` collection (24h
freshness, geospatially fuzzy via `$near`) before a real Sentinel Hub call is made.
Route handlers are `async def` and offload the blocking Mongo/Sentinel Hub calls to a
thread via `asyncio.to_thread`, so one slow Copernicus request doesn't stall other
in-flight requests on the same worker.

---

## Status

Phase 1 (MVP) is functional end-to-end against real Sentinel-2/Sentinel-3 data and a
real MongoDB instance: `GET /` detects the user's location and redirects to `GET /map`,
which renders a Folium map with an NDVI/heat-island summary for that area; `GET /api/area`
returns the same analysis as JSON; `GET /health` reports MongoDB connectivity. Results are
cached in MongoDB's `area_analyses` (24h freshness) and qualifying analyses are recorded
in `green_areas`/`heat_islands`, queryable via `$near`/`$geoWithin`/`$geoIntersects`.
`climate_shelters` stays empty — its Barcelona-model criteria (free access, AC, drinking
water, seating) describe a physical place, not something derivable from satellite pixels;
it needs a separate data source, out of scope for v1.

Full specification: [docs/SPEC.md](docs/SPEC.md).

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

One-time seed of Italy's official comuni list (ISTAT, snapshotted at
`data/istat_comuni.csv`) — not part of the automatic bootstrap above, since it's actual
data (7,896 documents) rather than empty collections/indexes:

```bash
python -m db.seed_comuni
```

---

## Project Structure

```
umbra/
├── api/
│   ├── routes/              # Flask endpoints
│   ├── services/            # Isolated business logic — key architectural boundary
│   ├── models/               # Domain models
│   └── app.py
├── processing/
│   ├── sentinel.py          # Copernicus data download and access
│   ├── ndvi.py               # NDVI computation from Sentinel-2 bands
│   ├── heat.py               # LST / heat island computation
│   └── geo.py                 # Coordinate validation, distance, bounding box
├── db/
│   └── mongo.py              # MongoDB connection and queries
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
| `FLASK_ENV` | No | `development` or `production` |

---

## Testing

```bash
pytest
```

Three levels in `tests/` — unit, integration, contract — all mocked via fixtures in
`tests/conftest.py`; no real external service is ever contacted. Full testing philosophy:
[docs/SPEC.md](docs/SPEC.md).

## Code quality

```bash
pip install -r requirements-dev.txt

ruff check .            # lint
ruff format --check .   # formatting (drop --check to auto-format)
mypy .                  # type check
```

All three run in CI (`.github/workflows/ci.yml`) as a separate `lint` job, alongside the
test suite.
