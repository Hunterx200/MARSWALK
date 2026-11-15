"""Terrain Cost Model for Mars Rover Surface Traverse.

Combines slope steepness, terrain roughness, and surface friction into
a unified traversal cost grid for A* navigation.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from algorithms.terrain.roughness import compute_roughness
from algorithms.terrain.slope import compute_slope_degrees


class TerrainCostModel:
    """Computes operational traversal cost grids for Mars surface navigation."""

    def __init__(
        self,
        max_slope_deg: float = 20.0,
        slope_weight: float = 3.0,
        roughness_weight: float = 1.5,
        impassable_cost: float = 1e6,
    ) -> None:
        """Initialize terrain cost model parameters.

        Args:
            max_slope_deg: Maximum slope angle (degrees) a rover can traverse.
                           Slopes exceeding this threshold are marked impassable.
            slope_weight: Scaling factor for slope traversal penalty.
            roughness_weight: Scaling factor for terrain roughness penalty.
            impassable_cost: High cost value representing impassable cells.
        """
        self.max_slope_deg = float(max_slope_deg)
        self.slope_weight = float(slope_weight)
        self.roughness_weight = float(roughness_weight)
        self.impassable_cost = float(impassable_cost)

    def compute_cost_grid(
        self,
        dem: np.ndarray,
        resolution_m: float = 10.0,
        slope_deg: Optional[np.ndarray] = None,
        roughness: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Generate 2D traversal cost grid from elevation data.

        Formula:
            If slope > max_slope_deg: cost = impassable_cost
            Else:
                slope_ratio = slope / max_slope_deg
                slope_cost = 1.0 + slope_weight * (slope_ratio ** 2)
                rough_cost = 1.0 + roughness_weight * normalized_roughness
                total_cost = slope_cost * rough_cost

        Returns:
            2D numpy array of cost multipliers (>= 1.0) with impassable cells
            set to impassable_cost.
        """
        if slope_deg is None:
            slope_deg = compute_slope_degrees(dem, resolution_m=resolution_m)

        if roughness is None:
            roughness = compute_roughness(dem, window_size=3)

        # Baseline cost multiplier is 1.0 (flat, smooth terrain)
        cost_grid = np.ones_like(dem, dtype=float)

        # 1. Slope penalty (quadratic growth as slope approaches threshold)
        slope_ratio = np.clip(slope_deg / max(1.0, self.max_slope_deg), 0.0, 1.0)
        slope_cost = 1.0 + self.slope_weight * (slope_ratio**2)

        # 2. Roughness penalty (normalized between 0 and 1)
        r_max = np.max(roughness)
        if r_max > 1e-4:
            norm_roughness = roughness / r_max
        else:
            norm_roughness = np.zeros_like(roughness)
        rough_cost = 1.0 + self.roughness_weight * norm_roughness

        # Combine costs
        cost_grid = slope_cost * rough_cost

        # Mark impassable slopes
        impassable_mask = slope_deg > self.max_slope_deg
        cost_grid[impassable_mask] = self.impassable_cost

        return cost_grid
