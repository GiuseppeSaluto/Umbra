"""Contract tests - verify the interface between api/services/ (area analysis)
and map/renderer.py (Folium rendering) stays consistent.
"""

import pytest

from api.services.area_service import get_area_analysis
from map.renderer import render_map

REQUIRED_ANALYSIS_KEYS_FOR_RENDER_MAP = {
    "ndvi_mean",
    "heat_island_coverage_pct",
    "acquisition_date",
    "source",
}


def test_get_area_analysis_output_satisfies_render_map_contract(mock_sentinel, modena_center):
    """Whatever get_area_analysis() returns must expose every key render_map()
    reads from its analysis argument.
    """
    analysis = get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert REQUIRED_ANALYSIS_KEYS_FOR_RENDER_MAP <= analysis.keys()


def test_render_map_fails_loudly_if_analysis_is_missing_a_required_key(modena_center):
    """If api/services/area_service.py ever drops a key render_map() relies on,
    the contract must break loudly (KeyError) - not silently render a map with
    blank/garbled popup text.
    """
    incomplete_analysis = {
        "ndvi_mean": 0.4,
        "heat_island_coverage_pct": 10.0,
        # missing acquisition_date and source
    }
    with pytest.raises(KeyError):
        render_map(modena_center["lat"], modena_center["lon"], radius_m=500, analysis=incomplete_analysis)


def test_render_map_accepts_the_real_get_area_analysis_output_end_to_end(mock_sentinel, modena_center):
    """The real (unmocked) output of get_area_analysis() must be directly
    consumable by render_map() with no adapter/reshaping in between.
    """
    analysis = get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)
    html = render_map(modena_center["lat"], modena_center["lon"], radius_m=500, analysis=analysis)
    assert "<html" in html.lower()
