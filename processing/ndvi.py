"""NDVI computation from Sentinel-2 bands (B4, B8). Phase 1 - MVP."""

import numpy as np


def calculate_ndvi(b4: np.ndarray, b8: np.ndarray) -> np.ndarray:
    """Compute the Normalized Difference Vegetation Index.

    NDVI = (B8 - B4) / (B8 + B4)

    Values above 0.3 indicate dense vegetation, values below 0 indicate
    impermeable surfaces (asphalt, buildings). Pixels where B8 + B4 == 0
    are resolved to 0 instead of raising a division-by-zero error.
    """
    if b4.shape != b8.shape:
        raise ValueError(
            f"b4 and b8 must have the same shape, got {b4.shape} and {b8.shape}"
        )

    denominator = b8.astype(np.float64) + b4.astype(np.float64)
    denominator = np.where(denominator == 0, np.finfo(np.float64).eps, denominator)
    return (b8.astype(np.float64) - b4.astype(np.float64)) / denominator
