"""Resolve a free-text place name to coordinates."""

import processing.geocoding as geocoding_module


def resolve_place(place: str) -> dict:
    """Return {"lat", "lon", "display_name"} for the given place name.

    Raises ValueError if the place is blank or no match is found.
    """
    if not place or not place.strip():
        raise ValueError("place name must not be empty")

    result = geocoding_module.geocode(place.strip())
    if result is None:
        raise ValueError(f"no location found for {place!r}")
    return result
