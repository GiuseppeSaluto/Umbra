"""
conftest.py - Umbra Test Suite
Fixtures shared across all test levels (unit, integration, contract).
No real service is contacted during tests.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


# ----------------------------------------------------------------
# FIXTURE: Synthetic raster data (Sentinel-2)
# ----------------------------------------------------------------

@pytest.fixture
def sample_b4():
    """Synthetic B4 (red) band - 10x10 pixel array."""
    return np.array([
        [0.05, 0.06, 0.30, 0.31, 0.28, 0.05, 0.07, 0.30, 0.29, 0.06],
        [0.06, 0.05, 0.29, 0.32, 0.27, 0.06, 0.05, 0.31, 0.28, 0.07],
        [0.30, 0.29, 0.28, 0.30, 0.29, 0.31, 0.30, 0.28, 0.29, 0.30],
        [0.31, 0.32, 0.30, 0.29, 0.30, 0.30, 0.31, 0.29, 0.30, 0.31],
        [0.05, 0.06, 0.29, 0.30, 0.05, 0.06, 0.05, 0.30, 0.29, 0.05],
        [0.06, 0.05, 0.30, 0.31, 0.06, 0.05, 0.06, 0.31, 0.30, 0.06],
        [0.28, 0.29, 0.30, 0.29, 0.30, 0.29, 0.28, 0.29, 0.30, 0.29],
        [0.29, 0.30, 0.31, 0.30, 0.29, 0.30, 0.29, 0.30, 0.31, 0.30],
        [0.05, 0.06, 0.28, 0.29, 0.06, 0.05, 0.07, 0.29, 0.28, 0.06],
        [0.06, 0.05, 0.29, 0.30, 0.05, 0.06, 0.05, 0.30, 0.29, 0.05],
    ], dtype=np.float32)


@pytest.fixture
def sample_b8():
    """Synthetic B8 (near infrared) band - 10x10 pixel array.
    High values where B4 is low = vegetation zones.
    Low values where B4 is high = impermeable zones (asphalt).
    """
    return np.array([
        [0.45, 0.43, 0.25, 0.24, 0.26, 0.44, 0.42, 0.24, 0.25, 0.43],
        [0.43, 0.45, 0.26, 0.23, 0.27, 0.43, 0.45, 0.23, 0.26, 0.42],
        [0.25, 0.26, 0.27, 0.25, 0.26, 0.24, 0.25, 0.27, 0.26, 0.25],
        [0.24, 0.23, 0.25, 0.26, 0.25, 0.25, 0.24, 0.26, 0.25, 0.24],
        [0.44, 0.43, 0.26, 0.25, 0.45, 0.43, 0.44, 0.25, 0.26, 0.45],
        [0.43, 0.45, 0.25, 0.24, 0.43, 0.45, 0.43, 0.24, 0.25, 0.43],
        [0.26, 0.25, 0.25, 0.26, 0.25, 0.26, 0.27, 0.26, 0.25, 0.26],
        [0.25, 0.24, 0.24, 0.25, 0.26, 0.25, 0.26, 0.25, 0.24, 0.25],
        [0.44, 0.43, 0.27, 0.26, 0.43, 0.45, 0.42, 0.26, 0.27, 0.43],
        [0.43, 0.45, 0.26, 0.25, 0.45, 0.43, 0.45, 0.25, 0.26, 0.45],
    ], dtype=np.float32)


@pytest.fixture
def sample_lst():
    """Synthetic Land Surface Temperature in Celsius - 10x10 pixel array.
    Vegetated zones: ~28C. Paved zones: ~42C (heat island).
    """
    return np.array([
        [28.1, 28.4, 41.8, 42.1, 41.5, 28.2, 28.6, 42.0, 41.7, 28.3],
        [28.4, 28.1, 41.5, 42.3, 41.2, 28.5, 28.1, 42.1, 41.4, 28.7],
        [41.8, 41.5, 41.2, 41.8, 41.5, 42.1, 41.8, 41.2, 41.5, 41.8],
        [42.1, 42.3, 41.8, 41.5, 41.8, 41.8, 42.1, 41.5, 41.8, 42.1],
        [28.2, 28.5, 41.5, 41.8, 28.1, 28.4, 28.2, 41.8, 41.5, 28.1],
        [28.5, 28.1, 41.8, 42.1, 28.4, 28.1, 28.5, 42.1, 41.8, 28.4],
        [41.5, 41.5, 41.8, 41.5, 41.8, 41.5, 41.2, 41.5, 41.8, 41.5],
        [41.5, 41.8, 42.1, 41.8, 41.5, 41.8, 41.5, 41.8, 42.1, 41.8],
        [28.1, 28.4, 41.2, 41.5, 28.4, 28.1, 28.7, 41.5, 41.2, 28.4],
        [28.4, 28.1, 41.5, 41.8, 28.1, 28.4, 28.1, 41.8, 41.5, 28.1],
    ], dtype=np.float32)


@pytest.fixture
def sample_ndvi_array(sample_b4, sample_b8):
    """NDVI precomputed from the synthetic B4/B8 samples."""
    denominator = sample_b8 + sample_b4
    denominator = np.where(denominator == 0, np.finfo(float).eps, denominator)
    return (sample_b8 - sample_b4) / denominator


@pytest.fixture
def sample_sentinel_response(sample_b4, sample_b8, sample_lst):
    """Full simulated response from fetch_area_data() in processing/sentinel.py."""
    return {
        "ndvi_b4": sample_b4,
        "ndvi_b8": sample_b8,
        "lst": sample_lst,
        "bbox": {
            "min_lon": 10.91,
            "min_lat": 44.62,
            "max_lon": 10.93,
            "max_lat": 44.64,
        },
        "acquisition_date": datetime(2026, 7, 1, 10, 30, tzinfo=timezone.utc),
        "cloud_coverage_pct": 3.2,
        "resolution_m_ndvi": 10,
        "resolution_m_lst": 1000,
        "source": "Sentinel-2 L2A + Sentinel-3 SLSTR (brightness temperature approximation)",
    }


# ----------------------------------------------------------------
# FIXTURE: MongoDB mock
# ----------------------------------------------------------------

@pytest.fixture
def mock_mongo_collection():
    """Mocked MongoDB collection with simulated geospatial behavior."""
    collection = MagicMock()

    sample_docs = [
        {
            "_id": "doc_001",
            "name": "Parco Ferrari",
            "type": "green_area",
            "location": {"type": "Point", "coordinates": [10.9252, 44.6371]},
            "ndvi_mean": 0.52,
            "shade_coverage_pct": 75,
            "has_water": True,
            "distance_m": 210,
            "last_updated": datetime(2026, 7, 1, tzinfo=timezone.utc),
        },
        {
            "_id": "doc_002",
            "name": "Biblioteca Delfini",
            "type": "climate_shelter",
            "location": {"type": "Point", "coordinates": [10.9235, 44.6458]},
            "indoor": True,
            "air_conditioned": True,
            "temp_celsius": 26,
            "distance_m": 480,
            "last_updated": datetime(2026, 7, 1, tzinfo=timezone.utc),
        },
    ]

    collection.find.return_value = iter(sample_docs)
    collection.find_one.return_value = None  # cache miss by default, mirrors mock_valkey
    collection.insert_one.return_value = MagicMock(inserted_id="new_doc_id")
    collection.count_documents.return_value = len(sample_docs)
    return collection


@pytest.fixture
def mock_mongo(mock_mongo_collection):
    """Full PyMongo patch for integration tests."""
    with patch("db.mongo.get_collection", return_value=mock_mongo_collection):
        yield mock_mongo_collection


# ----------------------------------------------------------------
# FIXTURE: Valkey mock
# ----------------------------------------------------------------

@pytest.fixture
def mock_valkey():
    """Mocked Valkey client - simulates a cache miss by default."""
    client = MagicMock()
    client.get.return_value = None   # cache miss by default
    client.set.return_value = True
    client.delete.return_value = 1
    client.exists.return_value = 0

    with patch("db.valkey_cache.get_client", return_value=client):
        yield client


@pytest.fixture
def mock_valkey_hit(mock_valkey):
    """Valkey with a cache hit - returns pre-serialized data."""
    import json
    cached = json.dumps({
        "type": "FeatureCollection",
        "features": [],
        "cached": True,
        "cache_ts": datetime.now(timezone.utc).isoformat(),
    })
    mock_valkey.get.return_value = cached.encode()
    return mock_valkey


# ----------------------------------------------------------------
# FIXTURE: Copernicus / Sentinel mock
# ----------------------------------------------------------------

@pytest.fixture
def mock_sentinel(sample_sentinel_response):
    """Patch of fetch_area_data() - no real calls to Copernicus."""
    with patch(
        "processing.sentinel.fetch_area_data",
        return_value=sample_sentinel_response
    ):
        yield sample_sentinel_response


# ----------------------------------------------------------------
# FIXTURE: Flask test client
# ----------------------------------------------------------------

@pytest.fixture
def app():
    """Flask app configured for testing - DB and services mocked."""
    from api.app import create_app
    application = create_app(testing=True)
    application.config.update({
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017/umbra_test",
        "VALKEY_URL": "redis://localhost:6379/1",
    })
    return application


@pytest.fixture
def client(app, mock_mongo, mock_valkey, mock_sentinel):
    """Flask HTTP client with all services mocked."""
    return app.test_client()


# ----------------------------------------------------------------
# FIXTURE: Geographic data
# ----------------------------------------------------------------

@pytest.fixture
def modena_center():
    """Downtown Modena coordinates - used as a geographic reference point in tests."""
    return {"lat": 44.6471, "lon": 10.9252}


@pytest.fixture
def sample_geojson_point():
    """Valid GeoJSON Point for schema tests."""
    return {
        "type": "Point",
        "coordinates": [10.9252, 44.6471]
    }


@pytest.fixture
def sample_geojson_polygon():
    """Valid GeoJSON Polygon (green area) for schema tests."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [10.920, 44.645],
            [10.930, 44.645],
            [10.930, 44.650],
            [10.920, 44.650],
            [10.920, 44.645],
        ]]
    }
