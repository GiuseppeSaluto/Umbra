import numpy as np
import pytest

from processing.heat import heat_island_coverage_pct, is_heat_island


def test_heat_mask_flags_hot_pixels(sample_lst):
    mask = is_heat_island(sample_lst)
    # sample_lst[0, 2] = 41.8 (paved, hot) - see conftest.py::sample_lst
    assert mask[0, 2]


def test_heat_mask_does_not_flag_cool_pixels(sample_lst):
    mask = is_heat_island(sample_lst)
    # sample_lst[0, 0] = 28.1 (vegetated, cool) - see conftest.py::sample_lst
    assert not mask[0, 0]


def test_heat_mask_shape_and_dtype_match_input(sample_lst):
    mask = is_heat_island(sample_lst)
    assert mask.shape == sample_lst.shape
    assert mask.dtype == np.bool_


def test_heat_mask_respects_custom_threshold(sample_lst):
    # With a threshold above every pixel in the sample, nothing is flagged.
    mask = is_heat_island(sample_lst, threshold=50.0)
    assert not mask.any()

    # With a threshold below every pixel in the sample, everything is flagged.
    mask = is_heat_island(sample_lst, threshold=0.0)
    assert mask.all()


def test_heat_island_coverage_pct_within_physical_range(sample_lst):
    pct = heat_island_coverage_pct(sample_lst)
    assert 0.0 <= pct <= 100.0


def test_heat_island_coverage_pct_consistent_with_mask(sample_lst):
    mask = is_heat_island(sample_lst, threshold=35.0)
    pct = heat_island_coverage_pct(sample_lst, threshold=35.0)
    expected = 100.0 * mask.sum() / mask.size
    assert pct == pytest.approx(expected)


def test_heat_island_coverage_pct_extremes(sample_lst):
    assert heat_island_coverage_pct(sample_lst, threshold=50.0) == 0.0
    assert heat_island_coverage_pct(sample_lst, threshold=0.0) == 100.0


def test_heat_mask_rejects_empty_array():
    with pytest.raises(ValueError):
        is_heat_island(np.array([]))
