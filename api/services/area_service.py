"""Area analysis - ties together Sentinel-2 fetch, NDVI, and heat island computation."""

import processing.sentinel as sentinel_module
from processing.geo import validate_coordinates
from processing.heat import heat_island_coverage_pct
from processing.ndvi import calculate_ndvi


def get_area_analysis(lat: float, lon: float, radius_m: float) -> dict:
    """Return an NDVI/LST summary for the area centered on (lat, lon)."""
    validate_coordinates(lat, lon)
    if radius_m <= 0:
        raise ValueError(f"radius_m must be positive, got {radius_m}")

    data = sentinel_module.fetch_area_data(lat, lon, radius_m)

    ndvi = calculate_ndvi(data["ndvi_b4"], data["ndvi_b8"])
    heat_pct = heat_island_coverage_pct(data["lst"])

    return {
        "bbox": data["bbox"],
        "ndvi_mean": float(ndvi.mean()),
        "ndvi_min": float(ndvi.min()),
        "ndvi_max": float(ndvi.max()),
        "heat_island_coverage_pct": heat_pct,
        "acquisition_date": data["acquisition_date"].isoformat(),
        "cloud_coverage_pct": data["cloud_coverage_pct"],
        "resolution_m": data["resolution_m"],
        "source": data["source"],
    }
