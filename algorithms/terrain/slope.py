"""Slope computation and gradient analysis for Digital Elevation Models (DEM).

Calculates surface slope in degrees using finite differences / Horn's method.
Applies Mars rover traversability classifications.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np


def compute_slope_degrees(
    dem: np.ndarray,
    resolution_m: float = 10.0,
) -> np.ndarray:
    """Calculate slope in degrees for each cell of a 2D elevation grid.

    Uses 2nd-order central differences for interior pixels and 1st-order forward/backward
    differences for edge boundaries:
        dz/dx = (z[y, x+1] - z[y, x-1]) / (2 * resolution_m)
        dz/dy = (z[y+1, x] - z[y-1, x]) / (2 * resolution_m)
        slope_rad = arctan(sqrt((dz/dx)^2 + (dz/dy)^2))
        slope_deg = degrees(slope_rad)

    Args:
        dem: 2D numpy array of elevation values in meters (height, width).
        resolution_m: Spatial resolution in meters per cell.

    Returns:
        2D numpy array of slopes in degrees, with identical shape as dem.
    """
    if dem.ndim != 2:
        raise ValueError(f"DEM must be a 2D array, got shape {dem.shape}")

    if resolution_m <= 0:
        raise ValueError(f"resolution_m must be positive, got {resolution_m}")

    height, width = dem.shape
    if height < 2 or width < 2:
        return np.zeros_like(dem, dtype=float)

    # Compute gradients along x (columns, axis=1) and y (rows, axis=0)
    # np.gradient uses central differences in interior and first differences at boundaries
    dy, dx = np.gradient(dem.astype(float), resolution_m)

    # Slope gradient magnitude
    gradient_magnitude = np.sqrt(dx**2 + dy**2)

    # Convert to slope angle in degrees
    slope_rad = np.arctan(gradient_magnitude)
    slope_deg = np.degrees(slope_rad)

    return slope_deg


def classify_slope_traversability(
    slope_deg: np.ndarray,
    max_safe_slope: float = 15.0,
    max_permissible_slope: float = 20.0,
) -> Dict[str, np.ndarray]:
    """Classify slopes into rover traversability categories.

    Nominal Perseverance/Curiosity rover operational parameters:
    - Gentle: < 5 deg (nominal cruise speed, negligible wheel slip)
    - Moderate: 5 - 15 deg (acceptable traverse, moderate power consumption)
    - Steep: 15 - 20 deg (restricted traverse, high slip risk, tactical check required)
    - Impassable: > 20 deg (strict rover keep-out zone)

    Returns:
        Dict of boolean masks for each class:
        'gentle', 'moderate', 'steep', 'impassable', 'traversable'
    """
    gentle = slope_deg < 5.0
    moderate = (slope_deg >= 5.0) & (slope_deg < max_safe_slope)
    steep = (slope_deg >= max_safe_slope) & (slope_deg <= max_permissible_slope)
    impassable = slope_deg > max_permissible_slope
    traversable = slope_deg <= max_permissible_slope

    return {
        "gentle": gentle,
        "moderate": moderate,
        "steep": steep,
        "impassable": impassable,
        "traversable": traversable,
    }
