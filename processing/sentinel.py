"""Download and access to Copernicus data (Sentinel-2 + Sentinel-3). Phase 1 - MVP.

NDVI comes from Sentinel-2 L2A (bands B04, B08, 10m resolution). Sentinel-2 has no
thermal band, so LST is approximated from Sentinel-3 SLSTR's S9 thermal channel
(brightness temperature, 1000m resolution) - see docs/SPEC.md for the accuracy
trade-off this implies (see AskUserQuestion discussion: brightness temperature is
not atmospherically-corrected split-window LST, but it is a defensible proxy for
relative hot/cool comparison at neighborhood scale).
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import numpy as np
from sentinelhub import (
    BBox,
    CRS,
    DataCollection,
    MimeType,
    SentinelHubCatalog,
    SentinelHubRequest,
    SHConfig,
    bbox_to_dimensions,
)
from sentinelhub.exceptions import BaseSentinelHubException

from processing.geo import bbox_from_point, validate_coordinates

logger = logging.getLogger(__name__)

CDSE_BASE_URL = "https://sh.dataspace.copernicus.eu"
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

NDVI_RESOLUTION_M = 10
LST_RESOLUTION_M = 1000
SEARCH_WINDOW_DAYS = 30
MAX_CLOUD_COVER_PCT = 50

_NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["B04", "B08"],
    output: { bands: 2, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) {
  return [sample.B04, sample.B08];
}
"""

_LST_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["S9"], units: "BRIGHTNESS_TEMPERATURE" }],
    output: { bands: 1, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) {
  return [sample.S9];
}
"""


def _build_config() -> SHConfig:
    config = SHConfig()
    config.sh_client_id = os.environ["COPERNICUS_CLIENT_ID"]
    config.sh_client_secret = os.environ["COPERNICUS_CLIENT_SECRET"]
    config.sh_base_url = CDSE_BASE_URL
    config.sh_token_url = CDSE_TOKEN_URL
    return config


def _cdse_collection(base_collection: DataCollection, name: str) -> DataCollection:
    """Redefine a DataCollection to point at the CDSE service URL.

    The Process API (SentinelHubRequest) prioritizes a DataCollection's own
    service_url over SHConfig.sh_base_url, so the default collections (which
    point at the legacy commercial Sentinel Hub service) must be redefined
    for requests to actually reach CDSE. SentinelHubCatalog does not have this
    quirk - it always follows config.sh_base_url - but redefining here too
    keeps both call sites consistent.
    """
    return base_collection.define_from(name, service_url=CDSE_BASE_URL)


def _default_time_interval() -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=SEARCH_WINDOW_DAYS)
    return start.isoformat(), end.isoformat()


def _first_band(array: np.ndarray) -> np.ndarray:
    """Drop a trailing singleton band dimension if present."""
    return array[..., 0] if array.ndim == 3 else array


def _find_best_scene(
    config: SHConfig, collection: DataCollection, bbox: BBox, time_interval: tuple[str, str]
) -> tuple[datetime, float]:
    """Return (acquisition_datetime, cloud_cover_pct) for the least cloudy Sentinel-2 scene."""
    catalog = SentinelHubCatalog(config=config)
    search_iterator = catalog.search(
        collection,
        bbox=bbox,
        time=time_interval,
        filter=f"eo:cloud_cover < {MAX_CLOUD_COVER_PCT}",
        fields={"include": ["properties.datetime", "properties.eo:cloud_cover"], "exclude": []},
    )
    results = list(search_iterator)
    if not results:
        raise RuntimeError(
            f"No Sentinel-2 scenes found in the requested area/time window "
            f"(last {SEARCH_WINDOW_DAYS} days, cloud cover < {MAX_CLOUD_COVER_PCT}%)"
        )

    best = min(results, key=lambda feature: feature["properties"]["eo:cloud_cover"])
    acquisition_date = datetime.fromisoformat(best["properties"]["datetime"].replace("Z", "+00:00"))
    cloud_cover_pct = float(best["properties"]["eo:cloud_cover"])
    return acquisition_date, cloud_cover_pct


def fetch_area_data(lat: float, lon: float, radius_m: float = 500) -> dict:
    """Fetch Sentinel-2 NDVI bands and a Sentinel-3 SLSTR brightness-temperature
    approximation of LST for the area centered on (lat, lon).
    """
    validate_coordinates(lat, lon)
    if radius_m <= 0:
        raise ValueError(f"radius_m must be positive, got {radius_m}")

    bbox_dict = bbox_from_point(lat, lon, radius_m)
    bbox = BBox(
        bbox=[bbox_dict["min_lon"], bbox_dict["min_lat"], bbox_dict["max_lon"], bbox_dict["max_lat"]],
        crs=CRS.WGS84,
    )

    config = _build_config()
    time_interval = _default_time_interval()

    s2_collection = _cdse_collection(DataCollection.SENTINEL2_L2A, "UMBRA_S2_L2A_CDSE")
    s3_collection = _cdse_collection(DataCollection.SENTINEL3_SLSTR, "UMBRA_S3_SLSTR_CDSE")

    acquisition_date, cloud_coverage_pct = _find_best_scene(config, s2_collection, bbox, time_interval)

    ndvi_request = SentinelHubRequest(
        evalscript=_NDVI_EVALSCRIPT,
        input_data=[SentinelHubRequest.input_data(
            data_collection=s2_collection,
            time_interval=time_interval,
            mosaicking_order="leastCC",
        )],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=bbox_to_dimensions(bbox, resolution=NDVI_RESOLUTION_M),
        config=config,
    )
    ndvi_bands = ndvi_request.get_data()[0]
    b4, b8 = ndvi_bands[..., 0], ndvi_bands[..., 1]

    lst_request = SentinelHubRequest(
        evalscript=_LST_EVALSCRIPT,
        input_data=[SentinelHubRequest.input_data(
            data_collection=s3_collection,
            time_interval=time_interval,
            mosaicking_order="leastCC",
        )],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=bbox_to_dimensions(bbox, resolution=LST_RESOLUTION_M),
        config=config,
    )
    try:
        lst_band = _first_band(lst_request.get_data()[0])
        if lst_band.size == 0:
            raise ValueError("Sentinel-3 SLSTR returned an empty response")
        lst_celsius = lst_band - 273.15
        source = "Sentinel-2 L2A + Sentinel-3 SLSTR (brightness temperature approximation)"
    except (BaseSentinelHubException, ValueError):
        logger.warning(
            "Sentinel-3 SLSTR has no LST coverage for this area/time window - "
            "continuing with NDVI only", exc_info=True
        )
        lst_celsius = None
        source = "Sentinel-2 L2A (Sentinel-3 SLSTR unavailable for this area)"

    return {
        "ndvi_b4": b4,
        "ndvi_b8": b8,
        "lst": lst_celsius,
        "bbox": bbox_dict,
        "acquisition_date": acquisition_date,
        "cloud_coverage_pct": cloud_coverage_pct,
        "resolution_m_ndvi": NDVI_RESOLUTION_M,
        "resolution_m_lst": LST_RESOLUTION_M,
        "source": source,
    }
