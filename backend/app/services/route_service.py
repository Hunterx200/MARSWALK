"""Route planning service integrating Developer C's AlternativeRoutePlanner engine."""
import logging
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


class RouteService:
    def __init__(self, terrain_svc=terrain_service, hazard_svc=hazard_service):
        self.terrain_svc = terrain_svc
        self.hazard_svc = hazard_svc
        self._planner: Optional[AlternativeRoutePlanner] = None
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
            hazard_mask = (slope_grid > 20.0)
        else:
            hazard_mask = np.zeros_like(dem, dtype=bool)

        hazard_score_grid = self.hazard_svc.get_hazard_score_grid()
        if hazard_score_grid is not None:
            hazard_mask = hazard_mask | (hazard_score_grid > 70.0)

        # Coordinate transformer: (grid_x=col, grid_y=row) -> (lon, lat)
        # Row 0 = 18.7°N (lat_max), Row 64 = 18.2°N (lat_min)
        # Col 0 = 77.0°E (lon_min), Col 102 = 77.8°E (lon_max)
        def grid_to_mars(grid_x: int, grid_y: int) -> Tuple[float, float]:
            u = float(grid_x) / max(1, w - 1)
            v = float(grid_y) / max(1, h - 1)
            lon = settings.min_lon + u * (settings.max_lon - settings.min_lon)
            lat = settings.max_lat - v * (settings.max_lat - settings.min_lat)
            return round(float(lon), 6), round(float(lat), 6)

        try:
            self._planner = AlternativeRoutePlanner(
                dem=dem,
                hazard_mask=hazard_mask,
                resolution_m=resolution_m,
                coord_transformer=grid_to_mars,
            )
            logger.info(f"Initialized Developer C AlternativeRoutePlanner with DEM shape {dem.shape} and {hazard_mask.sum()} hazard cells.")
        except Exception as e:
            logger.error(f"Failed to initialize AlternativeRoutePlanner: {e}")
            self._planner = None

    def validate_coordinates(self, coord: GeoCoordinate, name: str) -> None:
        """Verify coordinates fall within Jezero Crater bounding box."""
        if not (settings.min_lon <= coord.longitude <= settings.max_lon and
                settings.min_lat <= coord.latitude <= settings.max_lat):
            raise InvalidRequestException(
                message=f"{name} coordinate ({coord.longitude}, {coord.latitude}) is outside the Jezero Crater region "
                        f"[{settings.min_lon}, {settings.min_lat}, {settings.max_lon}, {settings.max_lat}]."
            )

    def _convert_path_result_to_route_item(
        self,
        path_res: PathResult,
        label: str,
        start_coord: GeoCoordinate,
        goal_coord: GeoCoordinate,
        elev_available: bool,
        now_iso: str,
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

        return RouteItem(
            id=f"route_{uuid.uuid4().hex[:8]}",
            label=label,
            algorithm="Developer C AlternativeRoutePlanner (A*)",
            profile=path_res.profile,
            start=start_coord,
            goal=goal_coord,
            path=path_nodes,
            distance_meters=round(path_res.total_distance_m, 1),
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
        )

    def plan_route(self, request: RoutePlanRequest) -> RoutePlanResponse:
        """Execute route planning using Developer C's AlternativeRoutePlanner."""
        now_iso = get_current_utc_iso()
        req_id = f"route_req_{uuid.uuid4().hex[:12]}"

        # Handle start and goal coordinates
        # 1. Geographic input (default contract)
        if request.start is not None and request.goal is not None:
            self.validate_coordinates(request.start, "Start")
            self.validate_coordinates(request.goal, "Goal")
            start_coord = request.start
            goal_coord = request.goal
            start_row, start_col = self.terrain_svc.geo_to_grid(start_coord.longitude, start_coord.latitude)
            goal_row, goal_col = self.terrain_svc.geo_to_grid(goal_coord.longitude, goal_coord.latitude)
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
            start_lon, start_lat = self.terrain_svc.grid_to_geo(start_row, start_col)
            goal_lon, goal_lat = self.terrain_svc.grid_to_geo(goal_row, goal_col)
            start_coord = GeoCoordinate(longitude=start_lon, latitude=start_lat)
            goal_coord = GeoCoordinate(longitude=goal_lon, latitude=goal_lat)
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
        # Parse profile option
        profile_str = (opts.profile or "balanced").lower()
        try:
            preferred_profile = RouteProfile(profile_str)
        except ValueError:
            preferred_profile = RouteProfile.BALANCED

        # Execute Developer C multi-route planning
        # start and goal in AlternativeRoutePlanner are (col, row) = (x, y)
        multi_res = self._planner.plan_multi_routes(
            start=(start_col, start_row),
            goal=(goal_col, goal_row),
            allow_diagonal=opts.allow_diagonal,
            preferred_profile=preferred_profile,
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
                )
                routes_out.append(alt_item)

        # Extract GeoJSON and comparison metrics from Developer C MultiRouteResult
        geojson_data = multi_res.to_geojson()
        multi_dict = multi_res.to_dict()
        comparison = multi_dict.get("comparison")

        return RoutePlanResponse(
            request_id=req_id,
            region_id=request.region_id,
            status="success",
            routes=routes_out,
            message="Route is a planning estimate and is not guaranteed safe.",
            geojson=geojson_data,
            comparison=comparison,
        )


route_service = RouteService()
