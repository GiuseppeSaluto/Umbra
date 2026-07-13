import numpy as np
import pytest

from processing.ndvi import calculate_ndvi


def test_ndvi_matches_expected_values(sample_b4, sample_b8, sample_ndvi_array):
    result = calculate_ndvi(sample_b4, sample_b8)
    np.testing.assert_allclose(result, sample_ndvi_array, rtol=1e-5)


def test_ndvi_is_within_physical_range(sample_b4, sample_b8):
    result = calculate_ndvi(sample_b4, sample_b8)
    assert result.min() >= -1.0
    assert result.max() <= 1.0


def test_ndvi_detects_vegetation_above_threshold(sample_b4, sample_b8):
    result = calculate_ndvi(sample_b4, sample_b8)
    # Rows/cols 0-1 and 4-5 in the synthetic sample are the vegetated pixels
    # (low B4, high B8) — see conftest.py::sample_b4/sample_b8.
    assert result[0, 0] > 0.3
    assert result[4, 4] > 0.3


def test_ndvi_flags_impermeable_surfaces_below_threshold(sample_b4, sample_b8):
    result = calculate_ndvi(sample_b4, sample_b8)
    # Rows/cols 2-3 in the synthetic sample are near-identical B4/B8
    # (asphalt-like, no vegetation signal) — NDVI should sit near zero.
    assert -0.1 < result[2, 2] < 0.1


def test_ndvi_handles_zero_denominator_without_raising():
    b4 = np.zeros((2, 2), dtype=np.float32)
    b8 = np.zeros((2, 2), dtype=np.float32)
    result = calculate_ndvi(b4, b8)
    assert np.all(np.isfinite(result))


def test_ndvi_shape_matches_input():
    b4 = np.full((5, 7), 0.2, dtype=np.float32)
    b8 = np.full((5, 7), 0.4, dtype=np.float32)
    result = calculate_ndvi(b4, b8)
    assert result.shape == (5, 7)


def test_ndvi_rejects_mismatched_shapes():
    b4 = np.zeros((10, 10), dtype=np.float32)
    b8 = np.zeros((5, 5), dtype=np.float32)
    with pytest.raises(ValueError):
        calculate_ndvi(b4, b8)
