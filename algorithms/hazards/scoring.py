"""Hazard scoring and risk evaluation for Mars exploration routes.

Computes hazard penalty grids and estimated risk scores.

DISCLAIMER & LIMITATION NOTICE:
All risk scores and hazard classifications are project-generated estimates
for mission-planning research and DO NOT represent certified NASA flight
safety determinations. Sub-meter obstacles (boulders < 1m, local regolith
fluidization, wheel sinkage) cannot be guaranteed detected by orbital data alone.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from algorithms.hazards.proximity import compute_hazard_distance_grid


class HazardRiskModel:
    """Evaluates hazard proximity penalties and composite risk scores."""

    DISCLAIMER: str = (
        "Project-generated risk estimate. NOT an official NASA safety determination. "
        "Never describe a generated route as guaranteed safe."
    )

    def __init__(
        self,
        hazard_buffer_m: float = 15.0,
        hard_standoff_m: float = 3.0,
        buffer_penalty_weight: float = 5.0,
        impassable_cost: float = 1e6,
    ) -> None:
        """Initialize hazard risk model.

        Args:
            hazard_buffer_m: Safe standoff distance around detected hazards.
            hard_standoff_m: Physical collision keep-out distance (deemed strictly impassable).
            buffer_penalty_weight: Traversal cost multiplier factor inside the buffer zone.
            impassable_cost: Cost assigned to impassable cells.
        """
        self.hazard_buffer_m = float(hazard_buffer_m)
        self.hard_standoff_m = float(hard_standoff_m)
        self.buffer_penalty_weight = float(buffer_penalty_weight)
        self.impassable_cost = float(impassable_cost)

    def compute_hazard_cost_grid(
        self,
        hazard_dist_grid: np.ndarray,
    ) -> np.ndarray:
        """Calculate traversal cost multiplier based on proximity to hazards.

        Cells closer than hard_standoff_m are marked impassable.
        Cells between hard_standoff_m and hazard_buffer_m receive a decaying penalty.
        Cells beyond hazard_buffer_m receive neutral cost multiplier 1.0.

        Returns:
            2D numpy array of hazard cost multipliers.
        """
        cost_grid = np.ones_like(hazard_dist_grid, dtype=float)

        # 1. Hard collision zone -> impassable
        impassable_mask = hazard_dist_grid <= self.hard_standoff_m
        cost_grid[impassable_mask] = self.impassable_cost

        # 2. Buffer zone penalty (smooth quadratic decay)
        buffer_mask = (hazard_dist_grid > self.hard_standoff_m) & (
            hazard_dist_grid < self.hazard_buffer_m
        )
        if np.any(buffer_mask):
            denom = max(1.0, self.hazard_buffer_m - self.hard_standoff_m)
            ratio = (self.hazard_buffer_m - hazard_dist_grid[buffer_mask]) / denom
            penalty = self.buffer_penalty_weight * (ratio**2)
            cost_grid[buffer_mask] = 1.0 + penalty

        return cost_grid

    def compute_composite_risk_grid(
        self,
        slope_deg: np.ndarray,
        hazard_dist_grid: np.ndarray,
        roughness: Optional[np.ndarray] = None,
        max_slope_deg: float = 20.0,
    ) -> np.ndarray:
        """Compute composite risk score (0.0 to 100.0) for every grid cell.

        Risk formula (0.0 - 100.0):
        - Slope Risk (0-40 pts): proportional to (slope / max_slope)^2
        - Hazard Proximity Risk (0-45 pts): max risk at hazard, decaying to 0 at buffer
        - Roughness Risk (0-15 pts): based on normalized surface irregularity

        Returns:
            2D numpy array with risk scores clamped to [0.0, 100.0].
        """
        # 1. Slope risk component (0 - 40 pts)
        slope_norm = np.clip(slope_deg / max(1.0, max_slope_deg), 0.0, 1.0)
        slope_risk = 40.0 * (slope_norm**2)
        # Any slope exceeding limit automatically scores 100
        slope_risk[slope_deg > max_slope_deg] = 100.0

        # 2. Hazard proximity risk component (0 - 45 pts)
        denom = max(1.0, self.hazard_buffer_m)
        prox_ratio = np.clip(
            (self.hazard_buffer_m - hazard_dist_grid) / denom, 0.0, 1.0
        )
        hazard_risk = 45.0 * prox_ratio
        # Inside hard standoff -> maximum risk
        hazard_risk[hazard_dist_grid <= self.hard_standoff_m] = 50.0

        # 3. Roughness risk component (0 - 15 pts)
        if roughness is not None:
            r_max = np.max(roughness)
            norm_rough = roughness / r_max if r_max > 1e-4 else np.zeros_like(roughness)
            rough_risk = 15.0 * norm_rough
        else:
            rough_risk = np.zeros_like(slope_deg)

        composite_risk = slope_risk + hazard_risk + rough_risk
        return np.clip(composite_risk, 0.0, 100.0)
