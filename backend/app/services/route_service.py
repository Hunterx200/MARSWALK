"""Route planning service integrating Developer C's AlternativeRoutePlanner engine."""
import logging
import math
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Ensure MARSWALK root is on sys.path so 'algorithms' can be imported anywhere
root_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from algorithms.models import RouteProfile, PathResult, Waypoint, MultiRouteResult
from algorithms.routing.alternatives import AlternativeRoutePlanner
from algorithms.routing.astar import AStarPlanner

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

logger = logging.getLogger(__name__)


class MarswalkAlternativeRoutePlanner(AlternativeRoutePlanner):
    """Enhanced multi-profile planner tailored for real MOLA DEM (463m resolution).
    
    Generates genuinely distinct physical routes for:
    - direct (Fastest): Shortest geometric traverse across terrain, minimal slope penalty.
    - balanced (Balanced): Energy and slope-aware model avoiding steeper slope ridges and moderate hazards.
    - safe (Safest): Strict slope avoidance (>2.5°) and wide hazard standoff (2200m buffer) avoiding rough terrain.
    """

    def plan_multi_routes(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        allow_diagonal: bool = True,
        preferred_profile: RouteProfile = RouteProfile.BALANCED,
        max_slope_deg: Optional[float] = None,
    ) -> MultiRouteResult:
        pref_str = (preferred_profile.value if hasattr(preferred_profile, "value") else str(preferred_profile)).lower()
        if pref_str in ("fastest", "direct"):
            pref_key = "direct"
        elif pref_str in ("safest", "safe"):
            pref_key = "safe"
        else:
            pref_key = "balanced"

        # 1. DIRECT: Pure distance, minimal slope penalty
        c_direct = 1.0 + 0.1 * (self.slope_grid / 20.0) ** 2

        # 2. BALANCED: Moderate slope penalty + moderate hazard avoidance (~900m = ~2 cells)
        h_buf_b = 900.0
        h_pen_b = np.where(self.hazard_dist_grid < h_buf_b, 1.0 + 4.0 * ((h_buf_b - self.hazard_dist_grid) / h_buf_b) ** 2, 1.0)
        c_balanced = (1.0 + 10.0 * (self.slope_grid / 10.0) ** 2) * h_pen_b

        # 3. SAFE: Strict slope penalty (penalizing slopes > 2.5°) + wide hazard buffer (~2200m = ~5 cells)
        h_buf_s = 2200.0
        h_pen_s = np.where(self.hazard_dist_grid < h_buf_s, 1.0 + 15.0 * ((h_buf_s - self.hazard_dist_grid) / h_buf_s) ** 2, 1.0)
        c_safe = (1.0 + 25.0 * (self.slope_grid / 10.0) ** 2) * h_pen_s

        # Apply hazard and boundary mask as impassable (np.inf) to all profile cost grids
        if hasattr(self, "hazard_mask") and self.hazard_mask is not None:
            c_direct[self.hazard_mask] = np.inf
            c_balanced[self.hazard_mask] = np.inf
            c_safe[self.hazard_mask] = np.inf

        req_slope = max_slope_deg if max_slope_deg is not None else 25.0
        cost_configs = {
            "direct": (c_direct, min(25.0, req_slope)),
            "balanced": (c_balanced, min(25.0, req_slope)),
            "safe": (c_safe, min(20.0, req_slope)),
        }

        routes: Dict[str, PathResult] = {}
        for p_name, (c_grid, max_s) in cost_configs.items():
            planner = AStarPlanner(
                cost_grid=c_grid,
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
            res = planner.plan(start=start, goal=goal, profile_name=p_name, max_slope_deg=max_s)
            routes[p_name] = res

        primary_route = routes.get(pref_key, routes["balanced"])
        other_keys = [k for k in ("balanced", "direct", "safe") if k != pref_key]
        alternatives = [routes[k] for k in other_keys if k in routes]

        return MultiRouteResult(primary=primary_route, alternatives=alternatives)


class RouteService:
    MAX_SNAP_DISTANCE_M: float = 800.0

    def __init__(self, terrain_svc=terrain_service, hazard_svc=hazard_service):
        self.terrain_svc = terrain_svc
        self.hazard_svc = hazard_svc
        self._planner: Optional[AlternativeRoutePlanner] = None
        self._routes: Dict[str, RouteItem] = {}
        self._init_planner()

    def _init_planner(self) -> None:
        """Initialize Developer C's AlternativeRoutePlanner with real NASA MOLA DEM and hazards."""
        if not self.terrain_svc.is_available or self.terrain_svc._elevation is None:
            logger.warning("Terrain service elevation is not available; planner cannot be initialized.")
            self._planner = None
            return

        dem = self.terrain_svc._elevation
        h, w = dem.shape
        resolution_m = 463.0

        # Construct hazard mask from actual slope and hazard grid (> 20 deg or hazard score > 70)
        slope_grid = self.terrain_svc._slope
        if slope_grid is not None:
            hazard_mask = (slope_grid > 20.0).copy()
        else:
            hazard_mask = np.zeros_like(dem, dtype=bool)

        hazard_score_grid = self.hazard_svc.get_hazard_score_grid()
        if hazard_score_grid is not None:
            hazard_mask = hazard_mask | (hazard_score_grid > 70.0)

        # Enforce inner traversable corridor: Row 64 and Col 102 centers fall outside
        # the mission exploration boundary [77.0°E-77.8°E, 18.2°N-18.7°N].
        # Mask them as impassable so graph search never visits them.
        hazard_mask[64, :] = True
        hazard_mask[:, 102] = True

        # PDS pixel-center coordinate mapping:
        # lon(col) = 77.00390625 + col / 128.0
        # lat(row) = 18.69921875 - row / 128.0
        def grid_to_mars(grid_x: int, grid_y: int) -> Tuple[float, float]:
            lon = 77.00390625 + grid_x / 128.0
            lat = 18.69921875 - grid_y / 128.0
            return round(float(lon), 6), round(float(lat), 6)

        try:
            self._planner = MarswalkAlternativeRoutePlanner(
                dem=dem,
                hazard_mask=hazard_mask,
                resolution_m=resolution_m,
                coord_transformer=grid_to_mars,
            )
            logger.info(f"Initialized MarswalkAlternativeRoutePlanner with DEM shape {dem.shape} and {hazard_mask.sum()} hazard cells.")
        except Exception as e:
            logger.error(f"Failed to initialize AlternativeRoutePlanner: {e}")
            self._planner = None

    def validate_coordinates(self, coord: GeoCoordinate, name: str) -> None:
        """Verify coordinates fall within Jezero Crater mission exploration bounding box."""
        if not (settings.min_lon <= coord.longitude <= settings.max_lon and
                settings.min_lat <= coord.latitude <= settings.max_lat):
            raise InvalidRequestException(
                message=f"{name} coordinate ({coord.longitude}, {coord.latitude}) is outside the Jezero Crater region "
                        f"[{settings.min_lon}, {settings.min_lat}, {settings.max_lon}, {settings.max_lat}]."
            )

    def snap_endpoint(self, coord: GeoCoordinate, name: str) -> Tuple[int, int, GeoCoordinate, float]:
        """
        Map endpoint to nearest traversable grid cell (col in 0..101, row in 0..63).
        If endpoint maps to non-traversable edge cells (col=102 or row=64),
        maps it to the nearest traversable cell if within MAX_SNAP_DISTANCE_M.
        Returns (row, col, snapped_geo_coord, snap_distance_m).
        """
        u = (coord.longitude - 77.00390625) * 128.0
        v = (18.69921875 - coord.latitude) * 128.0
        col_raw = int(round(u))
        row_raw = int(round(v))

        col_snap = max(0, min(101, col_raw))
        row_snap = max(0, min(63, row_raw))

        lon_snap = 77.00390625 + col_snap / 128.0
        lat_snap = 18.69921875 - row_snap / 128.0

        # Physical distance on Mars sphere (R = 3,396,190m) at Jezero sub-tropics
        lat_rad = math.radians(18.45)
        dx = (coord.longitude - lon_snap) * (math.pi / 180.0) * 3396190.0 * math.cos(lat_rad)
        dy = (coord.latitude - lat_snap) * (math.pi / 180.0) * 3396190.0
        snap_dist_m = math.hypot(dx, dy)

        if snap_dist_m > self.MAX_SNAP_DISTANCE_M:
            raise InvalidRequestException(
                message=f"{name} coordinate ({coord.longitude}, {coord.latitude}) requires snapping distance of {snap_dist_m:.1f}m, which exceeds maximum allowed {self.MAX_SNAP_DISTANCE_M}m."
            )

        snapped_coord = GeoCoordinate(longitude=round(lon_snap, 6), latitude=round(lat_snap, 6))
        return row_snap, col_snap, snapped_coord, round(snap_dist_m, 1)

    def validate_emitted_geojson(self, geojson_data: dict) -> None:
        """Validate that all LineString coordinates fall strictly within mission boundary."""
        for feat in geojson_data.get("features", []):
            if feat.get("geometry", {}).get("type") == "LineString":
                coords = feat.get("geometry", {}).get("coordinates", [])
                for idx, pt in enumerate(coords):
                    lon, lat = pt[0], pt[1]
                    if not (77.0 <= lon <= 77.8 and 18.2 <= lat <= 18.7):
                        raise InvalidRequestException(
                            message=f"Waypoint {idx} ({lon:.6f}°E, {lat:.6f}°N) exceeds mission exploration boundary [77.0°E-77.8°E, 18.2°N-18.7°N]."
                        )

    def _convert_path_result_to_route_item(
        self,
        path_res: PathResult,
        label: str,
        start_coord: GeoCoordinate,
        goal_coord: GeoCoordinate,
        elev_available: bool,
        now_iso: str,
        original_start: Optional[GeoCoordinate] = None,
        snapped_start: Optional[GeoCoordinate] = None,
        start_snap_dist: float = 0.0,
        original_goal: Optional[GeoCoordinate] = None,
        snapped_goal: Optional[GeoCoordinate] = None,
        goal_snap_dist: float = 0.0,
    ) -> RouteItem:
        """Convert Developer C PathResult to API RouteItem adhering to contract."""
        path_nodes: List[PathNode] = []
        for wp in path_res.waypoints:
            lon = wp.lon if wp.lon is not None else start_coord.longitude
            lat = wp.lat if wp.lat is not None else start_coord.latitude
            path_nodes.append(
                PathNode(
                    longitude=lon,
                    latitude=lat,
                    row=wp.grid_y,
                    column=wp.grid_x,
                )
            )

        # Risk level determination based on Developer C risk score and slope
        if path_res.max_slope_deg < 10.0 and path_res.estimated_risk_score < 35.0:
            risk_level = "low"
        elif path_res.max_slope_deg < 20.0 and path_res.estimated_risk_score < 65.0:
            risk_level = "medium"
        else:
            risk_level = "high"

        # Traversal time in minutes (Developer C computes estimated_traverse_time_hr)
        travel_time_min = path_res.estimated_traverse_time_hr * 60.0

        # Maximum hazard score from waypoints
        max_hazard = path_res.estimated_risk_score
        if path_res.waypoints:
            max_hazard = max(w.risk_score for w in path_res.waypoints)

        total_distance = round(path_res.total_distance_m + start_snap_dist + goal_snap_dist, 1)

        route_item = RouteItem(
            id=f"route_{uuid.uuid4().hex[:8]}",
            label=label,
            algorithm="Developer C AlternativeRoutePlanner (A*)",
            profile=path_res.profile,
            start=start_coord,
            goal=goal_coord,
            path=path_nodes,
            distance_meters=total_distance,
            estimated_travel_time_minutes=round(travel_time_min, 1),
            mean_slope_degrees=round(path_res.avg_slope_deg, 2),
            maximum_slope_degrees=round(path_res.max_slope_deg, 2),
            mean_hazard_score=round(path_res.estimated_risk_score, 1),
            maximum_hazard_score=round(max_hazard, 1),
            risk_level=risk_level,
            data_coverage=RouteDataCoverage(
                elevation="available" if elev_available else "unavailable",
                hazards="available" if elev_available else "unavailable",
            ),
            warnings=path_res.warnings,
            provenance=RouteProvenance(
                generated_at=now_iso,
                cost_model=f"Developer C Multi-Profile ({path_res.profile}): distance + slope + hazard standoff",
                limitations=path_res.limitations or STANDARD_LIMITATIONS,
            ),
            risk_score=round(path_res.estimated_risk_score, 1),
            elevation_gain_m=round(path_res.total_elevation_gain_m, 1),
            elevation_loss_m=round(path_res.total_elevation_loss_m, 1),
            total_cost=round(path_res.total_cost, 2),
            waypoint_count=len(path_res.waypoints),
            original_start=original_start or start_coord,
            snapped_start=snapped_start or start_coord,
            start_snap_distance_m=round(start_snap_dist, 1),
            original_goal=original_goal or goal_coord,
            snapped_goal=snapped_goal or goal_coord,
            goal_snap_distance_m=round(goal_snap_dist, 1),
        )
        self._routes[route_item.id] = route_item
        return route_item

    def get_route(self, route_id: str) -> Optional[RouteItem]:
        """Retrieve a planned route by ID."""
        return self._routes.get(route_id)

    def plan_route(self, request: RoutePlanRequest) -> RoutePlanResponse:
        """Execute route planning using Developer C's AlternativeRoutePlanner."""
        now_iso = get_current_utc_iso()
        req_id = f"route_req_{uuid.uuid4().hex[:12]}"

        # Handle start and goal coordinates
        # 1. Geographic input (default contract)
        if request.start is not None and request.goal is not None:
            self.validate_coordinates(request.start, "Start")
            self.validate_coordinates(request.goal, "Goal")
            orig_start = request.start
            orig_goal = request.goal
            start_row, start_col, snapped_start, start_snap_dist = self.snap_endpoint(orig_start, "Start")
            goal_row, goal_col, snapped_goal, goal_snap_dist = self.snap_endpoint(orig_goal, "Goal")
            start_coord = orig_start
            goal_coord = orig_goal
        # 2. Grid input fallback (start_x, start_y, goal_x, goal_y)
        elif (request.start_x is not None and request.start_y is not None and
              request.goal_x is not None and request.goal_y is not None):
            start_col, start_row = request.start_x, request.start_y
            goal_col, goal_row = request.goal_x, request.goal_y
            h, w = self.terrain_svc.get_grid_dimensions()
            if not (0 <= start_col < w and 0 <= start_row < h):
                raise InvalidRequestException(
                    message=f"Start grid coordinate ({start_col}, {start_row}) is out of bounds [0..{w-1}, 0..{h-1}]."
                )
            if not (0 <= goal_col < w and 0 <= goal_row < h):
                raise InvalidRequestException(
                    message=f"Goal grid coordinate ({goal_col}, {goal_row}) is out of bounds [0..{w-1}, 0..{h-1}]."
                )
            # Inner grid clamping if grid inputs are on outer row/col
            start_col = min(101, start_col)
            start_row = min(63, start_row)
            goal_col = min(101, goal_col)
            goal_row = min(63, goal_row)
            start_lon, start_lat = self.terrain_svc.grid_to_geo(start_row, start_col)
            goal_lon, goal_lat = self.terrain_svc.grid_to_geo(goal_row, goal_col)
            orig_start = GeoCoordinate(longitude=start_lon, latitude=start_lat)
            orig_goal = GeoCoordinate(longitude=goal_lon, latitude=goal_lat)
            snapped_start = orig_start
            snapped_goal = orig_goal
            start_coord = orig_start
            goal_coord = orig_goal
            start_snap_dist = 0.0
            goal_snap_dist = 0.0
        else:
            raise InvalidRequestException(
                message="Start and Goal coordinates are required (either geographic start/goal or grid start_x/y, goal_x/y)."
            )

        elev_available = self.terrain_svc.is_available
        if not elev_available or self._planner is None:
            # Re-attempt planner initialization if terrain service loaded
            self._init_planner()
            if not elev_available or self._planner is None:
                return RoutePlanResponse(
                    request_id=req_id,
                    region_id=request.region_id,
                    status="failed",
                    routes=[],
                    message="Elevation terrain dataset is unavailable. Route cannot be planned safely without topography.",
                )

        opts = request.options or RouteOptions()
        # Parse profile option (support direct/fastest, safe/safest, balanced)
        profile_str = (opts.profile or request.profile or "balanced").lower()
        if profile_str in ("fastest", "direct"):
            preferred_profile = RouteProfile.DIRECT
        elif profile_str in ("safest", "safe"):
            preferred_profile = RouteProfile.SAFE
        else:
            preferred_profile = RouteProfile.BALANCED

        # Execute Developer C multi-route planning
        # start and goal in AlternativeRoutePlanner are (col, row) = (x, y)
        multi_res = self._planner.plan_multi_routes(
            start=(start_col, start_row),
            goal=(goal_col, goal_row),
            allow_diagonal=opts.allow_diagonal,
            preferred_profile=preferred_profile,
            max_slope_deg=opts.max_slope_degrees,
        )

        primary = multi_res.primary
        if not primary.found:
            # Handle blocked or unreachable
            status_msg_map = {
                "START_BLOCKED": f"Start coordinate ({start_coord.longitude}, {start_coord.latitude}) is located in impassable terrain.",
                "GOAL_BLOCKED": f"Goal coordinate ({goal_coord.longitude}, {goal_coord.latitude}) is located in impassable terrain.",
                "UNREACHABLE": "Destination is unreachable; terrain obstacles block all passable corridors.",
                "OUT_OF_BOUNDS": "Coordinates are outside the terrain grid boundary.",
            }
            msg = status_msg_map.get(primary.status, f"Route planning failed: {primary.message}")
            return RoutePlanResponse(
                request_id=req_id,
                region_id=request.region_id,
                status="failed",
                routes=[],
                message=msg,
            )

        # Build RouteItems for primary and requested alternatives
        routes_out: List[RouteItem] = []

        primary_item = self._convert_path_result_to_route_item(
            path_res=primary,
            label="Primary route",
            start_coord=start_coord,
            goal_coord=goal_coord,
            elev_available=elev_available,
            now_iso=now_iso,
            original_start=orig_start,
            snapped_start=snapped_start,
            start_snap_dist=start_snap_dist,
            original_goal=orig_goal,
            snapped_goal=snapped_goal,
            goal_snap_dist=goal_snap_dist,
        )
        routes_out.append(primary_item)

        # Include alternative routes up to requested count
        max_alts = opts.alternatives if opts.alternatives is not None else 2
        for idx, alt in enumerate(multi_res.alternatives[:max_alts], 1):
            if alt.found:
                alt_item = self._convert_path_result_to_route_item(
                    path_res=alt,
                    label=f"Alternative route {idx} ({alt.profile})",
                    start_coord=start_coord,
                    goal_coord=goal_coord,
                    elev_available=elev_available,
                    now_iso=now_iso,
                    original_start=orig_start,
                    snapped_start=snapped_start,
                    start_snap_dist=start_snap_dist,
                    original_goal=orig_goal,
                    snapped_goal=snapped_goal,
                    goal_snap_dist=goal_snap_dist,
                )
                routes_out.append(alt_item)

        # Extract GeoJSON and comparison metrics from Developer C MultiRouteResult
        geojson_data = multi_res.to_geojson()
        multi_dict = multi_res.to_dict()
        comparison = multi_dict.get("comparison")

        # Elevation sampling for endpoint connectors
        try:
            start_elev = self.terrain_svc.get_elevation_at(orig_start.longitude, orig_start.latitude)
        except Exception:
            start_elev = primary.waypoints[0].elevation_m if primary.waypoints else -2500.0

        try:
            goal_elev = self.terrain_svc.get_elevation_at(orig_goal.longitude, orig_goal.latitude)
        except Exception:
            goal_elev = primary.waypoints[-1].elevation_m if primary.waypoints else -2500.0

        # Inject endpoint connectors into GeoJSON LineString coordinates
        for feat in geojson_data.get("features", []):
            if feat.get("geometry", {}).get("type") == "LineString":
                coords = feat["geometry"]["coordinates"]
                if start_snap_dist > 0.0:
                    coords.insert(0, [orig_start.longitude, orig_start.latitude, round(float(start_elev), 1)])
                if goal_snap_dist > 0.0:
                    coords.append([orig_goal.longitude, orig_goal.latitude, round(float(goal_elev), 1)])
                if "distance_m" in feat.get("properties", {}):
                    feat["properties"]["distance_m"] = round(feat["properties"]["distance_m"] + start_snap_dist + goal_snap_dist, 1)

        # Validate that all emitted GeoJSON coordinates strictly stay within mission boundary
        self.validate_emitted_geojson(geojson_data)

        # Frontend convenience fields (matches frontend/src/types/api.ts)
        frontend_waypoints = []
        step_idx = 0
        if start_snap_dist > 0.0:
            frontend_waypoints.append({
                "index": step_idx,
                "lat": orig_start.latitude,
                "lon": orig_start.longitude,
                "elevation_m": round(float(start_elev), 1),
                "slope_deg": 0.0,
                "roughness": 0.2,
                "segment_distance_m": 0.0,
                "cumulative_distance_m": 0.0,
                "estimated_sol": 0.0,
                "risk_level": "LOW",
                "notes": "Start Point (Boundary Snapped)",
            })
            step_idx += 1

        cum_dist = start_snap_dist
        for i, wp in enumerate(primary.waypoints):
            cum_dist = start_snap_dist + wp.cumulative_distance_m
            seg_dist = (
                (wp.cumulative_distance_m - primary.waypoints[i - 1].cumulative_distance_m)
                if i > 0
                else start_snap_dist
            )
            frontend_waypoints.append({
                "index": step_idx,
                "lat": wp.lat if wp.lat is not None else orig_start.latitude,
                "lon": wp.lon if wp.lon is not None else orig_start.longitude,
                "elevation_m": round(wp.elevation_m, 1) if wp.elevation_m is not None else 0.0,
                "slope_deg": round(wp.slope_deg, 1) if wp.slope_deg is not None else 0.0,
                "roughness": round(wp.roughness_m, 2) if wp.roughness_m is not None else 0.2,
                "segment_distance_m": round(seg_dist, 1),
                "cumulative_distance_m": round(cum_dist, 1),
                "estimated_sol": round(cum_dist / 550.0, 1),
                "risk_level": "HIGH" if (wp.risk_score or 0) > 50 else ("MEDIUM" if (wp.risk_score or 0) > 25 else "LOW"),
                "notes": f"Waypoint {step_idx}",
            })
            step_idx += 1

        if goal_snap_dist > 0.0:
            cum_dist += goal_snap_dist
            frontend_waypoints.append({
                "index": step_idx,
                "lat": orig_goal.latitude,
                "lon": orig_goal.longitude,
                "elevation_m": round(float(goal_elev), 1),
                "slope_deg": 0.0,
                "roughness": 0.2,
                "segment_distance_m": round(goal_snap_dist, 1),
                "cumulative_distance_m": round(cum_dist, 1),
                "estimated_sol": round(cum_dist / 550.0, 1),
                "risk_level": "LOW",
                "notes": "Target Point (Boundary Snapped)",
            })

        path_coords: List[List[float]] = [
            [wp["lon"], wp["lat"]] for wp in frontend_waypoints
        ]

        frontend_alternatives = []
        for idx, alt in enumerate(multi_res.alternatives[:max_alts], 1):
            if alt.found:
                alt_coords = [
                    [wp.lon, wp.lat] for wp in alt.waypoints if wp.lon is not None and wp.lat is not None
                ]
                if start_snap_dist > 0.0:
                    alt_coords.insert(0, [orig_start.longitude, orig_start.latitude])
                if goal_snap_dist > 0.0:
                    alt_coords.append([orig_goal.longitude, orig_goal.latitude])
                frontend_alternatives.append({
                    "id": f"alt_{alt.profile}_{idx}",
                    "name": f"Alternative: {alt.profile.capitalize()}",
                    "profile": alt.profile,
                    "distance_m": round(alt.total_distance_m + start_snap_dist + goal_snap_dist, 1),
                    "duration_sols": round((alt.total_distance_m + start_snap_dist + goal_snap_dist) / 500.0, 1),
                    "max_slope_deg": round(alt.max_slope_deg, 1),
                    "avg_slope_deg": round(alt.avg_slope_deg, 1),
                    "risk_score": round(alt.estimated_risk_score, 1),
                    "risk_category": "HIGH" if alt.estimated_risk_score > 50 else ("MEDIUM" if alt.estimated_risk_score > 25 else "LOW"),
                    "science_targets_count": 2,
                    "waypoints": [
                        {
                            "index": wp.step_index,
                            "lat": wp.lat,
                            "lon": wp.lon,
                            "elevation_m": round(wp.elevation_m or 0.0, 1),
                            "slope_deg": round(wp.slope_deg or 0.0, 1),
                            "roughness": round(wp.roughness_m or 0.2, 2),
                            "segment_distance_m": round(
                                (wp.cumulative_distance_m - alt.waypoints[w_idx - 1].cumulative_distance_m)
                                if w_idx > 0
                                else 0.0,
                                1,
                            ),
                            "cumulative_distance_m": round(wp.cumulative_distance_m, 1),
                            "estimated_sol": round(wp.cumulative_distance_m / 500.0, 1),
                            "risk_level": "HIGH" if (wp.risk_score or 0) > 50 else "LOW",
                        }
                        for w_idx, wp in enumerate(alt.waypoints)
                    ],
                    "path_coordinates": alt_coords,
                    "description": f"Alternative route optimized for {alt.profile} profile.",
                })

        summary = {
            "total_distance_m": round(primary.total_distance_m + start_snap_dist + goal_snap_dist, 1),
            "estimated_duration_sols": round((primary.total_distance_m + start_snap_dist + goal_snap_dist) / 500.0, 1),
            "max_slope_deg": round(primary.max_slope_deg, 1),
            "avg_slope_deg": round(primary.avg_slope_deg, 1),
            "overall_risk_score": round(primary.estimated_risk_score, 1),
            "risk_category": "HIGH" if primary.estimated_risk_score > 50 else ("MEDIUM" if primary.estimated_risk_score > 25 else "LOW"),
            "energy_budget_kwh": round((primary.total_distance_m + start_snap_dist + goal_snap_dist) * 0.0012, 2),
        }

        provenance_dict = {
            "elevation_model": "NASA MGS MOLA MEGDR 128ppd Topography",
            "imagery_model": "NASA Mars Trek CTX Mosaic",
            "hazard_model": "Horn Slope Gradient & Distance Standoff Buffer",
            "generated_at": now_iso,
            "disclaimer": STANDARD_LIMITATIONS[0],
        }

        return RoutePlanResponse(
            request_id=req_id,
            region_id=request.region_id,
            status="success",
            routes=routes_out,
            message="Route is a planning estimate and is not guaranteed safe.",
            geojson=geojson_data,
            comparison=comparison,
            route_id=primary_item.id,
            algorithm="A* Pathfinding (Euclidean + Slope/Hazard Cost)",
            profile=primary.profile,
            summary=summary,
            waypoints=frontend_waypoints,
            path_coordinates=path_coords,
            alternatives=frontend_alternatives,
            warnings=primary.warnings,
            provenance=provenance_dict,
            original_start=orig_start,
            snapped_start=snapped_start,
            start_snap_distance_m=round(start_snap_dist, 1),
            original_goal=orig_goal,
            snapped_goal=snapped_goal,
            goal_snap_distance_m=round(goal_snap_dist, 1),
        )


route_service = RouteService()
