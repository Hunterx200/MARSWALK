"""Science Observation Planner for Mars Exploration.

Identifies, scores, and prioritizes scientific points of interest (POIs)
such as delta deposits, crater rims, carbonate outcrops, and sample cache sites.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from algorithms.models import GridCoordinate, MarsCoordinate


@dataclass
class ScienceTarget:
    """A scientific observation target in Jezero Crater."""

    target_id: str
    name: str
    target_type: str  # e.g., "delta_sediment", "crater_rim", "carbonate_outcrop", "sample_cache"
    grid_x: int
    grid_y: int
    lon: Optional[float] = None
    lat: Optional[float] = None
    scientific_priority: float = 1.0  # 1.0 (low) to 5.0 (highest)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScienceObservationPlanner:
    """Manages science targets and evaluates detour trade-offs."""

    def __init__(self, targets: Optional[List[ScienceTarget]] = None) -> None:
        self.targets: List[ScienceTarget] = targets or []

    def add_target(self, target: ScienceTarget) -> None:
        self.targets.append(target)

    def find_targets_near_path(
        self,
        path_grid: List[Tuple[int, int]],
        max_distance_cells: float = 5.0,
    ) -> List[Dict[str, Any]]:
        """Identify which science targets lie within a specified distance of a planned path.

        Args:
            path_grid: List of (x, y) coordinates along the planned path.
            max_distance_cells: Maximum distance in grid cells to consider adjacent.

        Returns:
            List of reachable science targets with minimum standoff distance.
        """
        nearby_targets: List[Dict[str, Any]] = []

        for target in self.targets:
            min_dist = float("inf")
            closest_step = -1

            for step_idx, (px, py) in enumerate(path_grid):
                d = math.hypot(px - target.grid_x, py - target.grid_y)
                if d < min_dist:
                    min_dist = d
                    closest_step = step_idx

            if min_dist <= max_distance_cells:
                target_dict = target.to_dict()
                target_dict["distance_to_path_cells"] = round(min_dist, 2)
                target_dict["closest_waypoint_step"] = closest_step
                nearby_targets.append(target_dict)

        # Sort by scientific priority descending
        nearby_targets.sort(key=lambda t: t["scientific_priority"], reverse=True)
        return nearby_targets
