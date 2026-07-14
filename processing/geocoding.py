import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Umbra/1.0 (climate refuge platform; github.com/GiuseppeSaluto/Umbra)"
REQUEST_TIMEOUT_S = 10


def geocode(place: str) -> dict | None:
    """Return {"lat", "lon", "display_name"} for the best match, or None if not found."""
    response = requests.get(
        NOMINATIM_URL,
        params={"q": place, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_S,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None

    best = results[0]
    return {
        "lat": float(best["lat"]),
        "lon": float(best["lon"]),
        "display_name": best["display_name"],
    }
