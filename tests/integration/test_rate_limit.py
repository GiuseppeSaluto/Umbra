"""Rate limiting - protects /api/area, /map and /search from hammering the
quota-limited external services behind them (Sentinel Hub, Nominatim).

Disabled by default in the shared `client` fixture (see conftest.py) so the
rest of the integration suite stays deterministic. This file builds its own
app with rate limiting explicitly forced on instead, which also gives it a
fresh, isolated in-memory limiter store (a new store is created every time
`create_app()` runs `limiter.init_app()`), so results never depend on
whatever other tests ran before it.
"""

import pytest

from api.app import create_app


@pytest.fixture
def rate_limited_client(mock_mongo, mock_sentinel):
    app = create_app(testing=True, rate_limiting=True)
    return app.test_client()


def test_api_area_returns_429_once_its_limit_is_exceeded(rate_limited_client, modena_center):
    query = {**modena_center, "radius_m": 500}
    for _ in range(20):
        response = rate_limited_client.get("/api/area", query_string=query)
        assert response.status_code == 200

    response = rate_limited_client.get("/api/area", query_string=query)
    assert response.status_code == 429


def test_map_returns_429_once_its_limit_is_exceeded(rate_limited_client, modena_center):
    query = {**modena_center, "radius_m": 500}
    for _ in range(20):
        response = rate_limited_client.get("/map", query_string=query)
        assert response.status_code == 200

    response = rate_limited_client.get("/map", query_string=query)
    assert response.status_code == 429


def test_search_returns_429_once_its_limit_is_exceeded(rate_limited_client, monkeypatch):
    from api.routes import index as index_route

    monkeypatch.setattr(
        index_route,
        "resolve_place",
        lambda place: {"lat": 44.6471, "lon": 10.9252, "display_name": "Modena"},
    )

    for _ in range(30):
        response = rate_limited_client.get("/search", query_string={"place": "Modena"})
        assert response.status_code == 302

    response = rate_limited_client.get("/search", query_string={"place": "Modena"})
    assert response.status_code == 429


def test_health_is_not_covered_by_the_strict_per_route_limits(rate_limited_client):
    for _ in range(25):
        assert rate_limited_client.get("/health").status_code in (200, 503)


def test_rate_limiting_is_disabled_by_default_in_the_shared_test_client(client, modena_center):
    query = {**modena_center, "radius_m": 500}
    for _ in range(25):
        response = client.get("/api/area", query_string=query)
        assert response.status_code == 200
