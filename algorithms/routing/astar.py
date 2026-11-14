"""A* Pathfinding Implementation for Mars Surface Navigation.

Provides a robust, 8-connected grid A* pathfinding algorithm tailored for
rover navigation across digital elevation models and hazard grids.

Features:
- Configurable start and goal coordinates (Grid or Mars Geographic)
- 8-connected grid movement with precise Euclidean distance metrics
- Corner-cutting prevention adjacent to impassable obstacles
- Admissible Octile/Euclidean heuristics ensuring optimal paths
- Multi-factor traversal cost support (slope, roughness, hazard buffers)
- Comprehensive failure handling (out of bounds, blocked endpoints, unreachable goals)
- Detailed waypoint generation with cumulative distance and elevation metrics
"""

from __future__ import annotations

import heapq
import math
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from algorithms.models import (
    GridCoordinate,
    MarsCoordinate,
    PathResult,
    RouteProfile,
    Waypoint,
)


class AStarPlanner:
    """A* Path Planner on a 2D Cost Grid."""

    # 8-direction movements: (dx, dy, base_distance_factor)
    # dx: col change, dy: row change
    DIRECTIONS_8: List[Tuple[int, int, float]] = [
        # Orthogonal moves (cost factor = 1.0)
        (1, 0, 1.0),
        (-1, 0, 1.0),
        (0, 1, 1.0),
        (0, -1, 1.0),
        # Diagonal moves (cost factor = sqrt(2) ≈ 1.41421356)
        (1, 1, math.sqrt(2)),
        (-1, 1, math.sqrt(2)),
        (1, -1, math.sqrt(2)),
        (-1, -1, math.sqrt(2)),
    ]

    DIRECTIONS_4: List[Tuple[int, int, float]] = [
        (1, 0, 1.0),
        (-1, 0, 1.0),
        (0, 1, 1.0),
        (0, -1, 1.0),
    ]

    def __init__(
        self,
        cost_grid: np.ndarray,
        resolution_m: float = 10.0,
        elevation_grid: Optional[np.ndarray] = None,
        slope_grid: Optional[np.ndarray] = None,
        roughness_grid: Optional[np.ndarray] = None,
        hazard_dist_grid: Optional[np.ndarray] = None,
        risk_grid: Optional[np.ndarray] = None,
        impassable_threshold: float = 1e6,
        allow_diagonal: bool = True,
        prevent_corner_cutting: bool = True,
        coord_transformer: Optional[Callable[[int, int], Tuple[float, float]]] = None,
    ) -> None:
        """Initialize the A* Planner with terrain and cost layers.

        Args:
            cost_grid: 2D array (height, width) representing traversal cost multipliers (>= 1.0)
                       or values >= impassable_threshold / np.inf for untraversable terrain.
            resolution_m: Ground sampling distance (meters per grid cell).
            elevation_grid: Optional 2D array of elevation in meters.
            slope_grid: Optional 2D array of slopes in degrees.
            roughness_grid: Optional 2D array of surface roughness values.
            hazard_dist_grid: Optional 2D array of distance to closest hazard in meters.
            risk_grid: Optional 2D array of estimated risk scores (0.0 to 100.0).
            impassable_threshold: Values at or above this are deemed impassable.
            allow_diagonal: Whether 8-connected diagonal movement is permitted.
            prevent_corner_cutting: If True, prevents diagonal movement if either adjacent
                                    orthogonal neighbor is impassable.
            coord_transformer: Optional callable (grid_x, grid_y) -> (lon, lat) to map
                               grid cells to Mars geographic coordinates.
        """
        if cost_grid.ndim != 2:
            raise ValueError(f"cost_grid must be 2D, got shape {cost_grid.shape}")

        self.cost_grid = cost_grid
        self.height, self.width = cost_grid.shape
        self.resolution_m = float(resolution_m)
        self.elevation_grid = elevation_grid
        self.slope_grid = slope_grid
        self.roughness_grid = roughness_grid
        self.hazard_dist_grid = hazard_dist_grid
        self.risk_grid = risk_grid
        self.impassable_threshold = float(impassable_threshold)
        self.allow_diagonal = allow_diagonal
        self.prevent_corner_cutting = prevent_corner_cutting
        self.coord_transformer = coord_transformer

        # Average rover operational speed on Mars (Perseverance ~0.04 m/s or 144 m/hr)
        self.nominal_speed_mps = 0.04

    def is_in_bounds(self, x: int, y: int) -> bool:
        """Check if grid coordinate (x=col, y=row) is within bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_passable(self, x: int, y: int) -> bool:
        """Check if a cell is within bounds and traversable."""
        if not self.is_in_bounds(x, y):
            return False
        val = self.cost_grid[y, x]
        if np.isnan(val) or np.isinf(val) or val >= self.impassable_threshold:
            return False
        return True

    def heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate admissible Octile distance heuristic in meters.

        Octile distance is admissible and consistent for 8-connected grids with
        orthogonal cost = 1.0 * resolution and diagonal cost = sqrt(2) * resolution.
        """
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        if self.allow_diagonal:
            # (sqrt(2) - 1) ≈ 0.41421356237
            h_grid = (dx + dy) + (math.sqrt(2) - 2.0) * min(dx, dy)
        else:
            # Manhattan distance
            h_grid = dx + dy
        return h_grid * self.resolution_m

    def plan(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        profile_name: str = RouteProfile.BALANCED.value,
        max_slope_deg: Optional[float] = None,
    ) -> PathResult:
        """Execute A* pathfinding from start to goal.

        Args:
            start: (x, y) starting grid coordinate (col, row).
            goal: (x, y) destination grid coordinate (col, row).
            profile_name: Name of the route profile used (e.g. "balanced", "safe", "direct").
            max_slope_deg: Optional runtime max slope filter.

        Returns:
            PathResult with detailed trajectory, waypoints, metrics, and safety caveats.
        """
        start_time = time.perf_counter()
        start_x, start_y = int(start[0]), int(start[1])
        goal_x, goal_y = int(goal[0]), int(goal[1])

        # 1. Validation: Bounds check
        if not self.is_in_bounds(start_x, start_y):
            return PathResult(
                found=False,
                status="OUT_OF_BOUNDS",
                message=f"Start coordinate ({start_x}, {start_y}) is outside grid bounds [0..{self.width-1}, 0..{self.height-1}].",
                profile=profile_name,
                execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        if not self.is_in_bounds(goal_x, goal_y):
            return PathResult(
                found=False,
                status="OUT_OF_BOUNDS",
                message=f"Goal coordinate ({goal_x}, {goal_y}) is outside grid bounds [0..{self.width-1}, 0..{self.height-1}].",
                profile=profile_name,
                execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 2. Validation: Start == Goal
        if (start_x, start_y) == (goal_x, goal_y):
            wp = self._build_single_waypoint(0, start_x, start_y, 0.0, 0.0)
            return PathResult(
                found=True,
                status="NO_CHANGE",
                message="Start and destination coordinates are identical. Rover is already at destination.",
                profile=profile_name,
                waypoints=[wp],
                path_grid=[(start_x, start_y)],
                execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 3. Validation: Start or Goal Passability
        if not self.is_passable(start_x, start_y):
            reason = self._diagnose_impassable_reason(start_x, start_y)
            return PathResult(
                found=False,
                status="START_BLOCKED",
                message=f"Start cell ({start_x}, {start_y}) is impassable: {reason}.",
                profile=profile_name,
                execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        if not self.is_passable(goal_x, goal_y):
            reason = self._diagnose_impassable_reason(goal_x, goal_y)
            return PathResult(
                found=False,
                status="GOAL_BLOCKED",
                message=f"Goal cell ({goal_x}, {goal_y}) is impassable: {reason}.",
                profile=profile_name,
                execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 4. A* Search Data Structures
        directions = self.DIRECTIONS_8 if self.allow_diagonal else self.DIRECTIONS_4

        # Priority Queue holds tuples: (f_score, counter, (x, y))
        counter = 0
        open_set: List[Tuple[float, int, Tuple[int, int]]] = []
        h_start = self.heuristic(start_x, start_y, goal_x, goal_y)
        heapq.heappush(open_set, (h_start, counter, (start_x, start_y)))

        # Cost from start along best known path
        g_score: Dict[Tuple[int, int], float] = {(start_x, start_y): 0.0}

        # Parent pointer mapping for path reconstruction
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}

        # Set of closed nodes
        closed_set: Set[Tuple[int, int]] = set()

        nodes_explored = 0
        path_found = False

        while open_set:
            current_f, _, current = heapq.heappop(open_set)
            curr_x, curr_y = current

            if current in closed_set:
                continue

            closed_set.add(current)
            nodes_explored += 1

            # Check if reached destination
            if (curr_x, curr_y) == (goal_x, goal_y):
                path_found = True
                break

            curr_g = g_score[current]
            curr_cost = self.cost_grid[curr_y, curr_x]

            # Expand neighbors
            for dx, dy, dist_factor in directions:
                next_x = curr_x + dx
                next_y = curr_y + dy
                neighbor = (next_x, next_y)

                if neighbor in closed_set:
                    continue

                if not self.is_passable(next_x, next_y):
                    continue

                # Runtime slope check if provided
                if max_slope_deg is not None and self.slope_grid is not None:
                    if self.slope_grid[next_y, next_x] > max_slope_deg:
                        continue

                # Corner cutting prevention:
                # If moving diagonally (dx != 0 and dy != 0), both adjacent orthogonal
                # cells must be passable to avoid clipping through obstacle corners.
                if self.prevent_corner_cutting and dx != 0 and dy != 0:
                    adj1_passable = self.is_passable(curr_x + dx, curr_y)
                    adj2_passable = self.is_passable(curr_x, curr_y + dy)
                    if not (adj1_passable and adj2_passable):
                        continue

                # Calculate step traversal cost
                next_cost = self.cost_grid[next_y, next_x]
                avg_cost_multiplier = (curr_cost + next_cost) * 0.5
                step_dist_m = dist_factor * self.resolution_m
                step_cost = step_dist_m * avg_cost_multiplier

                tentative_g = curr_g + step_cost

                if tentative_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g
                    came_from[neighbor] = current
                    h_val = self.heuristic(next_x, next_y, goal_x, goal_y)
                    f_val = tentative_g + h_val
                    counter += 1
                    heapq.heappush(open_set, (f_val, counter, neighbor))

        exec_time_ms = (time.perf_counter() - start_time) * 1000.0

        # 5. Handle Unreachable Goal
        if not path_found:
            return PathResult(
                found=False,
                status="UNREACHABLE",
                message=(
                    f"Destination ({goal_x}, {goal_y}) is unreachable from ({start_x}, {start_y}). "
                    f"No continuous passable path exists under the current terrain slope "
                    f"and hazard constraints. Explored {nodes_explored} nodes."
                ),
                profile=profile_name,
                nodes_explored=nodes_explored,
                execution_time_ms=exec_time_ms,
                warnings=[
                    "Path blocked by continuous terrain barrier, crater wall, or hazard buffer zone."
                ],
            )

        # 6. Path Reconstruction
        path_grid = self._reconstruct_path(came_from, (goal_x, goal_y))
        waypoints, metrics = self._build_waypoints_and_metrics(path_grid)

        traverse_time_hr = (
            metrics["total_distance_m"] / (self.nominal_speed_mps * 3600.0)
            if metrics["total_distance_m"] > 0
            else 0.0
        )

        warnings: List[str] = []
        if metrics["max_slope_deg"] >= 15.0:
            warnings.append(
                f"Route traverses steep terrain: maximum slope reaches {metrics['max_slope_deg']:.1f}°."
            )
        if metrics["min_hazard_dist_m"] < 15.0 and metrics["min_hazard_dist_m"] >= 0:
            warnings.append(
                f"Route approaches within {metrics['min_hazard_dist_m']:.1f}m of an identified hazard."
            )

        return PathResult(
            found=True,
            status="SUCCESS",
            message=f"Optimal {profile_name} route planned successfully.",
            profile=profile_name,
            waypoints=waypoints,
            path_grid=path_grid,
            total_distance_m=metrics["total_distance_m"],
            total_elevation_gain_m=metrics["elevation_gain_m"],
            total_elevation_loss_m=metrics["elevation_loss_m"],
            max_slope_deg=metrics["max_slope_deg"],
            avg_slope_deg=metrics["avg_slope_deg"],
            estimated_risk_score=metrics["estimated_risk_score"],
            total_cost=g_score.get((goal_x, goal_y), 0.0),
            estimated_traverse_time_hr=traverse_time_hr,
            nodes_explored=nodes_explored,
            execution_time_ms=exec_time_ms,
            warnings=warnings,
        )

    def _reconstruct_path(
        self, came_from: Dict[Tuple[int, int], Tuple[int, int]], current: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """Backtrack from goal to start to construct ordered list of coordinates."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def _build_single_waypoint(
        self,
        index: int,
        x: int,
        y: int,
        cumulative_dist: float,
        step_cost: float,
    ) -> Waypoint:
        """Create a Waypoint object for a specific cell."""
        lon, lat = None, None
        if self.coord_transformer is not None:
            lon, lat = self.coord_transformer(x, y)

        elev = (
            float(self.elevation_grid[y, x])
            if self.elevation_grid is not None
            else None
        )
        slope = (
            float(self.slope_grid[y, x])
            if self.slope_grid is not None
            else None
        )
        rough = (
            float(self.roughness_grid[y, x])
            if self.roughness_grid is not None
            else None
        )
        hdist = (
            float(self.hazard_dist_grid[y, x])
            if self.hazard_dist_grid is not None
            else None
        )
        risk = (
            float(self.risk_grid[y, x])
            if self.risk_grid is not None
            else (slope * 2.0 if slope is not None else 0.0)
        )
        risk = max(0.0, min(100.0, risk))

        return Waypoint(
            step_index=index,
            grid_x=x,
            grid_y=y,
            lon=lon,
            lat=lat,
            elevation_m=elev,
            slope_deg=slope,
            roughness_m=rough,
            hazard_dist_m=hdist,
            risk_score=risk,
            cumulative_distance_m=cumulative_dist,
            segment_cost=step_cost,
        )

    def _build_waypoints_and_metrics(
        self, path_grid: List[Tuple[int, int]]
    ) -> Tuple[List[Waypoint], Dict[str, float]]:
        """Construct waypoints and compute path metrics along the traversed trajectory."""
        waypoints: List[Waypoint] = []
        total_dist = 0.0
        elev_gain = 0.0
        elev_loss = 0.0
        slopes: List[float] = []
        risks: List[float] = []
        min_hazard_dist = float("inf")

        for i, (x, y) in enumerate(path_grid):
            if i > 0:
                prev_x, prev_y = path_grid[i - 1]
                dx = abs(x - prev_x)
                dy = abs(y - prev_y)
                is_diag = dx != 0 and dy != 0
                step_dist = (
                    math.sqrt(2) * self.resolution_m
                    if is_diag
                    else self.resolution_m
                )
                total_dist += step_dist

                # Elevation change
                if self.elevation_grid is not None:
                    de = (
                        self.elevation_grid[y, x]
                        - self.elevation_grid[prev_y, prev_x]
                    )
                    if de > 0:
                        elev_gain += de
                    else:
                        elev_loss += abs(de)

            wp = self._build_single_waypoint(i, x, y, total_dist, 0.0)
            waypoints.append(wp)

            if wp.slope_deg is not None:
                slopes.append(wp.slope_deg)
            risks.append(wp.risk_score)
            if wp.hazard_dist_m is not None:
                min_hazard_dist = min(min_hazard_dist, wp.hazard_dist_m)

        max_slope = max(slopes) if slopes else 0.0
        avg_slope = (sum(slopes) / len(slopes)) if slopes else 0.0

        # Weighted estimated risk score along the path
        # 60% average risk + 40% peak risk exposure
        avg_risk = (sum(risks) / len(risks)) if risks else 0.0
        max_risk = max(risks) if risks else 0.0
        path_risk = 0.6 * avg_risk + 0.4 * max_risk

        metrics = {
            "total_distance_m": total_dist,
            "elevation_gain_m": elev_gain,
            "elevation_loss_m": elev_loss,
            "max_slope_deg": max_slope,
            "avg_slope_deg": avg_slope,
            "estimated_risk_score": min(100.0, max(0.0, path_risk)),
            "min_hazard_dist_m": min_hazard_dist
            if min_hazard_dist != float("inf")
            else -1.0,
        }
        return waypoints, metrics

    def _diagnose_impassable_reason(self, x: int, y: int) -> str:
        """Provide a human-readable diagnosis why a cell is impassable."""
        reasons = []
        if self.slope_grid is not None:
            slope = self.slope_grid[y, x]
            if slope > 20.0:
                reasons.append(f"Slope exceeds limit ({slope:.1f}° > 20°)")
        if self.hazard_dist_grid is not None:
            dist = self.hazard_dist_grid[y, x]
            if dist < 5.0:
                reasons.append(f"Inside hazard zone (distance {dist:.1f}m < 5m)")
        if not reasons:
            reasons.append("High traversal cost / barrier")
        return ", ".join(reasons)
