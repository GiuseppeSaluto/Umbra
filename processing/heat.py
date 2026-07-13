"""LST / urban heat island computation. Phase 1 - MVP."""

import numpy as np

# Common reference threshold for extreme-heat alerts in EU/Mediterranean contexts.
DEFAULT_HEAT_THRESHOLD_C = 35.0


def is_heat_island(lst: np.ndarray, threshold: float = DEFAULT_HEAT_THRESHOLD_C) -> np.ndarray:
    """Return a boolean mask flagging pixels at or above the heat island threshold."""
    if lst.size == 0:
        raise ValueError("lst must not be empty")
    return lst >= threshold


def heat_island_coverage_pct(lst: np.ndarray, threshold: float = DEFAULT_HEAT_THRESHOLD_C) -> float:
    """Return the percentage of the area classified as heat island."""
    mask = is_heat_island(lst, threshold=threshold)
    return 100.0 * mask.sum() / mask.size
