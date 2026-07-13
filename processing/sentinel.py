"""Download and access to Copernicus (Sentinel-2) data. Phase 1 - MVP."""


def fetch_area_data(lat: float, lon: float, radius_m: int = 500) -> dict:
    """Download B4/B8 bands and LST for the requested area from Copernicus CDSE.

    Not implemented yet: contract defined in
    tests/conftest.py::sample_sentinel_response.
    """
    raise NotImplementedError
