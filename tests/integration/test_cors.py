"""CORS - only /api/* is meant to be called from a browser on a different
origin (e.g. a separate frontend consuming the JSON API directly). The
server-rendered HTML routes (/, /map, /search) are never fetched cross-origin,
so they carry no CORS headers.
"""


def test_api_area_allows_cross_origin_requests(client, modena_center):
    response = client.get(
        "/api/area",
        query_string={**modena_center, "radius_m": 500},
        headers={"Origin": "https://example.com"},
    )
    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"


def test_map_route_has_no_cors_header(client, modena_center):
    response = client.get(
        "/map",
        query_string={**modena_center, "radius_m": 500},
        headers={"Origin": "https://example.com"},
    )
    assert "Access-Control-Allow-Origin" not in response.headers


def test_index_route_has_no_cors_header(client):
    response = client.get("/", headers={"Origin": "https://example.com"})
    assert "Access-Control-Allow-Origin" not in response.headers
