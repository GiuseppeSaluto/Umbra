"""Contract tests - verify the interface between processing/ (raster computation,
Copernicus access) and api/services/area_service.py stays consistent. These don't
re-test business logic (unit/integration tests already cover that) - they lock in
the shape of the boundary itself, and check that a broken contract fails loudly
rather than silently producing wrong output.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from api.services.area_service import get_area_analysis
from processing.geo import bbox_from_point
from processing.heat import heat_island_coverage_pct
from processing.ndvi import calculate_ndvi

REQUIRED_SENTINEL_RESPONSE_KEYS = {
    "ndvi_b4",
    "ndvi_b8",
    "lst",
    "bbox",
    "acquisition_date",
    "cloud_coverage_pct",
    "resolution_m_ndvi",
    "resolution_m_lst",
    "source",
}

REQUIRED_BBOX_KEYS = {"min_lon", "min_lat", "max_lon", "max_lat"}


def test_sample_sentinel_response_satisfies_the_contract(sample_sentinel_response):
    """The canonical fixture for fetch_area_data()'s output must expose every key
    get_area_analysis() reads from it.
    """
    assert REQUIRED_SENTINEL_RESPONSE_KEYS <= sample_sentinel_response.keys()


def test_bbox_from_point_output_matches_what_area_service_expects(modena_center):
    """bbox_from_point() is the real function fetch_area_data() uses to build its
    bbox - its output must match what get_area_analysis passes straight through
    as the "bbox" field of the API response, with no key renaming in between.
    """
    bbox = bbox_from_point(modena_center["lat"], modena_center["lon"], radius_m=500)
    assert set(bbox.keys()) == REQUIRED_BBOX_KEYS


def test_acquisition_date_must_be_a_datetime_not_a_string(sample_sentinel_response):
    """get_area_analysis calls .isoformat() on acquisition_date - if fetch_area_data
    ever returned an already-formatted string, that call would raise an
    AttributeError deep inside a dict comprehension instead of failing at the
    actual contract boundary. Lock in the expected type here instead.
    """
    assert isinstance(sample_sentinel_response["acquisition_date"], datetime)


def test_ndvi_bands_are_shape_compatible_with_calculate_ndvi(sample_b4, sample_b8):
    """calculate_ndvi requires same-shape numpy arrays - lock in that the bands
    processing/sentinel.py provides satisfy that requirement.
    """
    result = calculate_ndvi(sample_b4, sample_b8)
    assert result.shape == sample_b4.shape == sample_b8.shape


def test_lst_array_is_compatible_with_heat_island_coverage_pct(sample_lst):
    """heat_island_coverage_pct expects a numpy array of Celsius temperatures -
    lock in that the contract fixture provides something it can consume.
    """
    pct = heat_island_coverage_pct(sample_lst)
    assert 0.0 <= pct <= 100.0


def test_get_area_analysis_fails_loudly_if_fetch_area_data_omits_a_required_key(
    modena_center, sample_sentinel_response
):
    """If processing/sentinel.py ever drops a key api/services/area_service.py
    relies on, the contract must break loudly (KeyError) - not silently return
    a result missing that data.
    """
    incomplete_response = {k: v for k, v in sample_sentinel_response.items() if k != "lst"}
    with patch("processing.sentinel.fetch_area_data", return_value=incomplete_response):
        with pytest.raises(KeyError):
            get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)


def test_get_area_analysis_fails_loudly_if_acquisition_date_is_not_a_datetime(modena_center, sample_sentinel_response):
    """A processing/ change that serializes acquisition_date to a string before
    returning it must break loudly too, not silently skip the .isoformat() call.
    """
    broken_response = {**sample_sentinel_response, "acquisition_date": "2026-07-01T10:30:00+00:00"}
    with patch("processing.sentinel.fetch_area_data", return_value=broken_response):
        with pytest.raises(AttributeError):
            get_area_analysis(modena_center["lat"], modena_center["lon"], radius_m=500)
