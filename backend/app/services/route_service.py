"""Route planning service implementing A* pathfinding on Mars terrain grid."""
import math
import heapq
import uuid
from typing import List, Tuple, Optional, Dict
import numpy as np

from app.config import settings
from app.core.errors import InvalidRequestException
from app.core.provenance import get_current_utc_iso, STANDARD_LIMITATIONS
from app.schemas.common import GeoCoordinate
from app.schemas.route import (
    RoutePlanRequest,
    RoutePlanResponse,
    RouteItem,
    PathNode,
    RouteDataCoverage,
    RouteProvenance,
    RouteOptions,
)
from app.services.terrain_service import terrain_service
from app.services.hazard_service import hazard_service

ROVER_SPEED_METERS_PER_SEC = 0.045  # ~162 m/hour nominal exploration traverse


class RouteService:
    def __init__(self, terrain_svc=terrain_service, hazard_svc=hazard_service):
        self.terrain_svc = terrain_svc
        self.hazard_svc = hazard_svc

    def validate_coordinates(self, coord: GeoCoordinate, name: str):
        """Verify coordinates fall within Jezero Crater bounding box."""
        if not (settings.min_lon <= coord.longitude <= settings.max_lon and
                settings.min_lat <= coord.latitude <= settings.max_lat):
            raise InvalidRequestException(
                message=f"{name} coordinate ({coord.longitude}, {coord.latitude}) is outside the Jezero Crater region "
                        f"[{settings.min_lon}, {settings.min_lat}, {settings.max_lon}, {settings.max_lat}]."
            )

    def _haversine_meters(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Compute surface distance on Mars in meters (Mars mean radius = 3389.5 km)."""
        r_mars = 3389500.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r_mars * c

    def _run_astar(
        self,
        start_rc: Tuple[int, int],
        goal_rc: Tuple[int, int],
        options: RouteOptions,
        slope_grid: Optional[np.ndarray],
        hazard_grid: Optional[np.ndarray],
    ) -> Optional[List[Tuple[int, int]]]:
        """A* search on grid graph with 8-connectivity."""
        h, w = self.terrain_svc.get_grid_dimensions()
        start_r, start_c = start_rc
        goal_r, goal_c = goal_rc

        if (start_r, start_c) == (goal_r, goal_c):
            return [(start_r, start_c)]

        cell_size = 463.0  # meters per grid cell
        open_set = []
        heapq.heappush(open_set, (0.0, 0.0, start_r, start_c))

        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score = { (start_r, start_c): 0.0 }

        # 8 directions: (dr, dc, base_dist)
        neighbors = [
            (-1, 0, cell_size),
            (1, 0, cell_size),
            (0, -1, cell_size),
            (0, 1, cell_size),
            (-1, -1, cell_size * 1.4142),
            (-1, 1, cell_size * 1.4142),
            (1, -1, cell_size * 1.4142),
            (1, 1, cell_size * 1.4142),
        ]

        def heuristic(r: int, c: int) -> float:
            dr = r - goal_r
            dc = c - goal_c
            return math.sqrt(dr * dr + dc * dc) * cell_size

        while open_set:
            _, current_g, curr_r, curr_c = heapq.heappop(open_set)

            if (curr_r, curr_c) == (goal_r, goal_c):
                # Reconstruct path
                path = [(curr_r, curr_c)]
                curr = (curr_r, curr_c)
                while curr in came_from:
                    curr = came_from[curr]
                    path.append(curr)
                path.reverse()
                return path

            if current_g > g_score.get((curr_r, curr_c), float('inf')):
                continue

            for dr, dc, step_dist in neighbors:
                nr, nc = curr_r + dr, curr_c + dc
                if 0 <= nr < h and 0 <= nc < w:
                    # Evaluate cost
                    cell_slope = 0.0
                    cell_hazard = 0.0
                    if slope_grid is not None:
                        cell_slope = float(slope_grid[nr, nc])
                    if hazard_grid is not None:
                        cell_hazard = float(hazard_grid[nr, nc])

                    # Slope constraint
                    if cell_slope > options.max_slope_degrees:
                        if options.avoid_hazards:
                            # Severe penalty or impassable
                            continue
                        else:
                            slope_multiplier = 5.0
                    else:
                        slope_multiplier = 1.0 + options.slope_weight * ((cell_slope / max(options.max_slope_degrees, 1.0)) ** 2)

                    hazard_multiplier = 1.0
                    if options.avoid_hazards and hazard_grid is not None:
                        hazard_multiplier = 1.0 + options.hazard_weight * (cell_hazard / 100.0)

                    step_cost = step_dist * options.distance_weight * slope_multiplier * hazard_multiplier
                    tentative_g = current_g + step_cost

                    if tentative_g < g_score.get((nr, nc), float('inf')):
                        came_from[(nr, nc)] = (curr_r, curr_c)
                        g_score[(nr, nc)] = tentative_g
                        f_score = tentative_g + heuristic(nr, nc)
                        heapq.heappush(open_set, (f_score, tentative_g, nr, nc))

        return None

    def plan_route(self, request: RoutePlanRequest) -> RoutePlanResponse:
        """Execute route planning according to requested options."""
        now_iso = get_current_utc_iso()
        req_id = f"route_req_{uuid.uuid4().hex[:12]}"

        # Validate coordinate boundaries
        self.validate_coordinates(request.start, "Start")
        self.validate_coordinates(request.goal, "Goal")

        # Map geographic coordinates to terrain grid
        start_row, start_col = self.terrain_svc.geo_to_grid(request.start.longitude, request.start.latitude)
        goal_row, goal_col = self.terrain_svc.geo_to_grid(request.goal.longitude, request.goal.latitude)

        elev_available = self.terrain_svc.is_available
        slope_grid = self.terrain_svc._slope if elev_available else None
        hazard_grid = self.hazard_svc.get_hazard_score_grid() if elev_available else None

        opts = request.options or RouteOptions()
        route_variants = [
            ("Primary route", opts),
        ]

        # Generate alternatives by adjusting weights as requested in contract rules
        if opts.alternatives >= 1:
            alt1_opts = RouteOptions(
                max_slope_degrees=max(5.0, opts.max_slope_degrees - 5.0),
                avoid_hazards=True,
                hazard_weight=0.5,
                slope_weight=0.6,
                distance_weight=0.2,
                alternatives=0
            )
            route_variants.append(("Alternative route 1 (Conservative / Minimum Slope)", alt1_opts))

        if opts.alternatives >= 2:
            alt2_opts = RouteOptions(
                max_slope_degrees=min(40.0, opts.max_slope_degrees + 5.0),
                avoid_hazards=opts.avoid_hazards,
                hazard_weight=0.2,
                slope_weight=0.2,
                distance_weight=0.7,
                alternatives=0
            )
            route_variants.append(("Alternative route 2 (Direct Traverse)", alt2_opts))

        routes_out: List[RouteItem] = []

        for idx, (label, variant_opts) in enumerate(route_variants):
            grid_path = self._run_astar(
                (start_row, start_col),
                (goal_row, goal_col),
                variant_opts,
                slope_grid,
                hazard_grid,
            )

            if not grid_path:
                continue

            path_nodes: List[PathNode] = []
            slopes_along_path: List[float] = []
            hazards_along_path: List[float] = []
            total_dist_meters = 0.0

            prev_lon, prev_lat = None, None
            for r, c in grid_path:
                lon, lat = self.terrain_svc.grid_to_geo(r, c)
                path_nodes.append(PathNode(longitude=lon, latitude=lat, row=r, column=c))
                
                if prev_lon is not None and prev_lat is not None:
                    step_meters = self._haversine_meters(prev_lon, prev_lat, lon, lat)
                    total_dist_meters += step_meters
                prev_lon, prev_lat = lon, lat

                if slope_grid is not None:
                    slopes_along_path.append(float(slope_grid[r, c]))
                if hazard_grid is not None:
                    hazards_along_path.append(float(hazard_grid[r, c]))

            # Fallback if path is a single point
            if total_dist_meters == 0.0 and len(path_nodes) > 1:
                total_dist_meters = 463.0 * (len(path_nodes) - 1)

            mean_slope = float(np.mean(slopes_along_path)) if slopes_along_path else 0.0
            max_slope = float(np.max(slopes_along_path)) if slopes_along_path else 0.0
            mean_hazard = float(np.mean(hazards_along_path)) if hazards_along_path else 0.0
            max_hazard = float(np.max(hazards_along_path)) if hazards_along_path else 0.0

            # Travel time estimate in minutes
            est_minutes = (total_dist_meters / ROVER_SPEED_METERS_PER_SEC) / 60.0
            # Additional penalty for mean slope
            if mean_slope > 5.0:
                est_minutes *= (1.0 + (mean_slope - 5.0) * 0.05)

            # Determine risk level
            if max_slope < 10.0 and max_hazard < 35.0:
                risk_level = "low"
            elif max_slope < 20.0 and max_hazard < 65.0:
                risk_level = "medium"
            else:
                risk_level = "high"

            warnings = []
            if not elev_available:
                warnings.append("MOLA elevation data is unavailable; route calculated on straight-line grid distance.")
            if max_slope > 15.0:
                warnings.append(f"Maximum route slope ({max_slope:.1f}°) exceeds nominal rover cruising limit (15°).")
            if max_hazard > 60.0:
                warnings.append(f"Route crosses elevated hazard sector with maximum score {max_hazard:.1f}.")

            routes_out.append(
                RouteItem(
                    id=f"route_{uuid.uuid4().hex[:8]}",
                    label=label,
                    algorithm="A*",
                    start=request.start,
                    goal=request.goal,
                    path=path_nodes,
                    distance_meters=round(total_dist_meters, 1),
                    estimated_travel_time_minutes=round(est_minutes, 1),
                    mean_slope_degrees=round(mean_slope, 2),
                    maximum_slope_degrees=round(max_slope, 2),
                    mean_hazard_score=round(mean_hazard, 1),
                    maximum_hazard_score=round(max_hazard, 1),
                    risk_level=risk_level,
                    data_coverage=RouteDataCoverage(
                        elevation="available" if elev_available else "unavailable",
                        hazards="available" if elev_available else "unavailable",
                    ),
                    warnings=warnings,
                    provenance=RouteProvenance(
                        generated_at=now_iso,
                        cost_model="distance + slope + hazard proximity (Backend A* fallback implementation)",
                        limitations=STANDARD_LIMITATIONS,
                    ),
                )
            )

        if not routes_out:
            return RoutePlanResponse(
                request_id=req_id,
                region_id=request.region_id,
                status="failed",
                routes=[],
                message="No passable route could be planned within slope and hazard constraints.",
            )

        return RoutePlanResponse(
            request_id=req_id,
            region_id=request.region_id,
            status="success",
            routes=routes_out,
            message="Route is a planning estimate and is not guaranteed safe.",
        )


route_service = RouteService()
