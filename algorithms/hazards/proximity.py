"""Hazard proximity calculation for Mars surface navigation.

Calculates exact Euclidean distance (in meters) from every grid cell to the
nearest identified hazard or keep-out feature.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt


def compute_hazard_distance_grid(
    hazard_mask: np.ndarray,
    resolution_m: float = 10.0,
) -> np.ndarray:
    """Compute Euclidean distance to the nearest hazard cell.

    Args:
        hazard_mask: 2D boolean or binary array (1/True = hazard, 0/False = clear).
        resolution_m: Grid resolution in meters per cell.

    Returns:
        2D numpy array of float distances in meters to the closest hazard cell.
        Cells that are themselves hazards have distance = 0.0.
    """
    if hazard_mask.ndim != 2:
        raise ValueError(f"hazard_mask must be 2D, got shape {hazard_mask.shape}")

    bool_mask = hazard_mask.astype(bool)

    # If no hazards exist on the grid, return infinite/large distance everywhere
    if not np.any(bool_mask):
        return np.full(hazard_mask.shape, 1e5, dtype=float)

    # If entire grid is hazards, return 0 everywhere
    if np.all(bool_mask):
        return np.zeros(hazard_mask.shape, dtype=float)

    # distance_transform_edt calculates distance to the nearest zero (background)
    # We want distance to the nearest True (hazard), so invert the mask:
    # 0 where hazard is present, 1 where clear.
    clear_mask = ~bool_mask

    # Distance in pixel units
    pixel_distances = distance_transform_edt(clear_mask)

    # Convert to physical meters
    meter_distances = pixel_distances * resolution_m

    return meter_distances
