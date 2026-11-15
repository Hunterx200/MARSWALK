"""Alternative Route Generator for Mars Exploration & Mission Planning.

Generates multiple distinct route alternatives (Direct, Safe, Balanced)
with varying trade-offs between traversal distance, energy expenditure,
and estimated hazard risk.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from algorithms.hazards.proximity import compute_hazard_distance_grid
from algorithms.hazards.scoring import HazardRiskModel
from algorithms.models import (
    GridCoordinate,
    MultiRouteResult,
    PathResult,
    RouteProfile,
    RouteRequest,
)
from algorithms.routing.astar import AStarPlanner
from algorithms.terrain.cost_model import TerrainCostModel
from algorithms.terrain.roughness import compute_roughness
from algorithms.terrain.slope import compute_slope_degrees


class AlternativeRoutePlanner:
    """Orchestrates multi-profile route generation across terrain and hazard layers."""

    def __init__(
        self,
        dem: np.ndarray,
        hazard_mask: Optional[np.ndarray] = None,
        resolution_m: float = 10.0,
        coord_transformer: Optional[Callable[[int, int], Tuple[float, float]]] = None,
    ) -> None:
        """Initialize the Alternative Route Planner with terrain data.

        Args:
            dem: 2D Digital Elevation Model array (elevations in meters).
            hazard_mask: Optional 2D boolean array (True = hazard).
            resolution_m: Spatial resolution in meters per cell.
            coord_transformer: Optional function (grid_x, grid_y) -> (lon, lat).
        """
        self.dem = dem
        self.height, self.width = dem.shape
        self.resolution_m = float(resolution_m)
        self.coord_transformer = coord_transformer

        # 1. Precompute Terrain Layers
        self.slope_grid = compute_slope_degrees(dem, resolution_m=self.resolution_m)
        self.roughness_grid = compute_roughness(dem, window_size=3)

        # 2. Precompute Hazard Layers
        if hazard_mask is not None:
            self.hazard_mask = hazard_mask.astype(bool)
        else:
            self.hazard_mask = np.zeros_like(dem, dtype=bool)

        self.hazard_dist_grid = compute_hazard_distance_grid(
            self.hazard_mask, resolution_m=self.resolution_m
        )

        # 3. Standardized Baseline Risk Grid for objective comparison across all profiles
        self.standard_risk_model = HazardRiskModel(
            hazard_buffer_m=20.0,
            hard_standoff_m=3.0,
        )
        self.standard_risk_grid = self.standard_risk_model.compute_composite_risk_grid(
            slope_deg=self.slope_grid,
            hazard_dist_grid=self.hazard_dist_grid,
            roughness=self.roughness_grid,
            max_slope_deg=20.0,
        )

    def plan_multi_routes(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        allow_diagonal: bool = True,
        preferred_profile: RouteProfile = RouteProfile.BALANCED,
    ) -> MultiRouteResult:
        """Generate primary route along with alternative routes for comparison.

        Profiles generated:
        - BALANCED: Nominal trade-off between traverse distance and hazard proximity.
        - DIRECT: Prioritizes shortest distance, minimal detour, standard slope limits.
        - SAFE: Prioritizes maximum standoff from hazards, strict slope thresholds (<14°),
                and gentle terrain.

        Returns:
            MultiRouteResult containing primary route, alternatives, and comparative metrics.
        """
        # Configure profiles with customized cost models and hazard buffers
        profile_configs: Dict[str, Dict[str, Any]] = {
            RouteProfile.BALANCED.value: {
                "max_slope_deg": 20.0,
                "slope_weight": 3.0,
                "roughness_weight": 1.5,
                "hazard_buffer_m": 15.0,
                "hazard_weight": 4.0,
                "hard_standoff_m": 3.0,
            },
            RouteProfile.DIRECT.value: {
                "max_slope_deg": 20.0,
                "slope_weight": 0.5,  # Minimal penalty on slope if below max
                "roughness_weight": 0.2,
                "hazard_buffer_m": 6.0,  # Small standoff buffer
                "hazard_weight": 1.0,
                "hard_standoff_m": 2.5,
            },
            RouteProfile.SAFE.value: {
                "max_slope_deg": 18.0,  # Conservative slope threshold (nominal 20 deg, safe 18 deg)
                "slope_weight": 6.0,  # Steep penalty for even moderate slopes
                "roughness_weight": 3.0,
                "hazard_buffer_m": 25.0,  # Wide safety buffer
                "hazard_weight": 10.0,  # Heavy avoidance penalty
                "hard_standoff_m": 5.0,
            },
        }

        routes: Dict[str, PathResult] = {}

        for prof_name, cfg in profile_configs.items():
            # Build terrain cost layer for this profile
            t_model = TerrainCostModel(
                max_slope_deg=cfg["max_slope_deg"],
                slope_weight=cfg["slope_weight"],
                roughness_weight=cfg["roughness_weight"],
            )
            terrain_cost = t_model.compute_cost_grid(
                self.dem,
                resolution_m=self.resolution_m,
                slope_deg=self.slope_grid,
                roughness=self.roughness_grid,
            )

            # Build hazard risk and cost layer for this profile
            h_model = HazardRiskModel(
                hazard_buffer_m=cfg["hazard_buffer_m"],
                hard_standoff_m=cfg["hard_standoff_m"],
                buffer_penalty_weight=cfg["hazard_weight"],
            )
            hazard_cost = h_model.compute_hazard_cost_grid(self.hazard_dist_grid)
            composite_risk = h_model.compute_composite_risk_grid(
                slope_deg=self.slope_grid,
                hazard_dist_grid=self.hazard_dist_grid,
                roughness=self.roughness_grid,
                max_slope_deg=cfg["max_slope_deg"],
            )

            # Combined cost grid (terrain cost * hazard cost)
            combined_cost = terrain_cost * hazard_cost

            planner = AStarPlanner(
                cost_grid=combined_cost,
                resolution_m=self.resolution_m,
                elevation_grid=self.dem,
                slope_grid=self.slope_grid,
                roughness_grid=self.roughness_grid,
                hazard_dist_grid=self.hazard_dist_grid,
                risk_grid=self.standard_risk_grid,
                allow_diagonal=allow_diagonal,
                prevent_corner_cutting=True,
                coord_transformer=self.coord_transformer,
            )

            res = planner.plan(
                start=start,
                goal=goal,
                profile_name=prof_name,
                max_slope_deg=cfg["max_slope_deg"],
            )
            routes[prof_name] = res

        # Primary route selection based on preference
        primary_key = preferred_profile.value
        primary_route = routes.get(primary_key, routes[RouteProfile.BALANCED.value])

        # Alternatives are the remaining profiles
        alternatives = [res for name, res in routes.items() if name != primary_key]

        return MultiRouteResult(primary=primary_route, alternatives=alternatives)
