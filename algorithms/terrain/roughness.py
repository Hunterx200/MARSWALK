"""Terrain roughness analysis for Mars surface navigation.

Calculates local elevation variance / roughness to identify rocky outcrops,
rubble fields, and uneven terrain.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter


def compute_roughness(
    dem: np.ndarray,
    window_size: int = 3,
) -> np.ndarray:
    """Compute local terrain roughness as local standard deviation of elevation.

    Roughness = sqrt(E[Z^2] - (E[Z])^2) over a local window.
    This effectively highlights rocky fields, scarp edges, and boulder areas.

    Args:
        dem: 2D numpy array of elevations in meters.
        window_size: Size of the neighborhood kernel (must be odd, default 3).

    Returns:
        2D numpy array of standard deviation (roughness in meters) per cell.
    """
    if dem.ndim != 2:
        raise ValueError(f"DEM must be a 2D array, got shape {dem.shape}")

    if window_size < 3 or window_size % 2 == 0:
        window_size = 3

    dem_f = dem.astype(float)

    # Local mean of Z
    mean = uniform_filter(dem_f, size=window_size, mode="reflect")

    # Local mean of Z^2
    mean_sq = uniform_filter(dem_f**2, size=window_size, mode="reflect")

    # Variance = E[Z^2] - (E[Z])^2
    variance = np.maximum(mean_sq - mean**2, 0.0)
    roughness = np.sqrt(variance)

    return roughness
