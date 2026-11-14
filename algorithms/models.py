"""Data models and type definitions for MARSWALK pathfinding and terrain analysis.

Defines coordinate models, route requests, waypoints, and route evaluation results.
Enforces clear coordinate semantics to prevent confusion between grid coordinates
(column, row) and Mars geographic coordinates (longitude, latitude).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class CoordinateType(str, Enum):
    """Semantic type of coordinate."""

    GRID = "grid"
    MARS_GEOGRAPHIC = "mars_geographic"


@dataclass(frozen=True)
class GridCoordinate:
    """Integer grid coordinates (x: column, y: row).

    Origin (0, 0) is at the top-left (North-West) corner of the raster grid:
    - x increases eastward (columns from 0 to width - 1).
    - y increases southward (rows from 0 to height - 1).
    """

    x: int
    y: int

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "type": CoordinateType.GRID.value}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GridCoordinate:
        return cls(x=int(data["x"]), y=int(data["y"]))


@dataclass(frozen=True)
class MarsCoordinate:
    """Mars geographic coordinates (longitude East, latitude North).

    Coordinate convention follows standard IAU/NASA Mars 2000 planetographic / planetocentric:
    - lon: Degrees East (positive 0 to 360, or -180 to +180).
      Jezero Crater is centered at approx 77.45°E.
    - lat: Degrees North (positive -90 to +90).
      Jezero Crater is centered at approx 18.38°N.
    """

    lon: float
    lat: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.lon, self.lat)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lon": self.lon,
            "lat": self.lat,
            "type": CoordinateType.MARS_GEOGRAPHIC.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarsCoordinate:
        return cls(lon=float(data["lon"]), lat=float(data["lat"]))


class RouteProfile(str, Enum):
    """Routing optimization profile."""

    DIRECT = "direct"  # Prioritize shortest distance
    SAFE = "safe"  # Prioritize maximum hazard buffer and gentle slopes
    BALANCED = "balanced"  # Trade-off between distance, energy, and safety margin
    SCIENCE = "science"  # Bias toward scientific interest zones / observations


@dataclass
class GridSpec:
    """Specification of the grid spatial reference and bounds."""

    width: int
    height: int
    resolution_m: float  # Ground sampling distance (meters per grid cell)
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float
    crs: str = "Mars 2000 / Equirectangular"
    description: str = "Jezero Crater Region"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouteRequest:
    """Specification of a path planning request."""

    start: Union[GridCoordinate, MarsCoordinate]
    goal: Union[GridCoordinate, MarsCoordinate]
    profile: RouteProfile = RouteProfile.BALANCED
    max_slope_deg: float = 20.0  # Rover hard limit (Perseverance threshold ~20 deg)
    hazard_buffer_m: float = 15.0  # Safe standoff distance from detected hazards
    allow_diagonal: bool = True
    generate_alternatives: bool = True

    def to_dict(self) -> Dict[str, Any]:
        start_dict = (
            self.start.to_dict()
            if hasattr(self.start, "to_dict")
            else dict(self.start)
        )
        goal_dict = (
            self.goal.to_dict() if hasattr(self.goal, "to_dict") else dict(self.goal)
        )
        return {
            "start": start_dict,
            "goal": goal_dict,
            "profile": self.profile.value,
            "max_slope_deg": self.max_slope_deg,
            "hazard_buffer_m": self.hazard_buffer_m,
            "allow_diagonal": self.allow_diagonal,
            "generate_alternatives": self.generate_alternatives,
        }


@dataclass
class Waypoint:
    """A navigational waypoint along a planned route."""

    step_index: int
    grid_x: int
    grid_y: int
    lon: Optional[float] = None
    lat: Optional[float] = None
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    roughness_m: Optional[float] = None
    hazard_dist_m: Optional[float] = None
    risk_score: float = 0.0  # Estimated risk score 0.0 - 100.0
    cumulative_distance_m: float = 0.0
    segment_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PathResult:
    """Result of an A* pathfinding query."""

    found: bool
    status: str  # "SUCCESS", "UNREACHABLE", "START_BLOCKED", "GOAL_BLOCKED", "OUT_OF_BOUNDS", "NO_CHANGE"
    message: str
    profile: str = RouteProfile.BALANCED.value
    waypoints: List[Waypoint] = field(default_factory=list)
    path_grid: List[Tuple[int, int]] = field(default_factory=list)

    # Metrics
    total_distance_m: float = 0.0
    total_elevation_gain_m: float = 0.0
    total_elevation_loss_m: float = 0.0
    max_slope_deg: float = 0.0
    avg_slope_deg: float = 0.0
    estimated_risk_score: float = 0.0  # 0 to 100 scale
    total_cost: float = 0.0
    estimated_traverse_time_hr: float = 0.0  # Based on ~0.04 m/s (144 m/hr) nominal traverse
    nodes_explored: int = 0
    execution_time_ms: float = 0.0

    # Safety caveats and provenance
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(
        default_factory=lambda: [
            "Project-generated risk estimate. NOT an official NASA safety determination.",
            "Never describe a generated route as guaranteed safe.",
            "Sub-meter obstacles and local sand entrapment cannot be guaranteed detected by orbital data alone.",
        ]
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "status": self.status,
            "message": self.message,
            "profile": self.profile,
            "total_distance_m": round(self.total_distance_m, 2),
            "total_elevation_gain_m": round(self.total_elevation_gain_m, 2),
            "total_elevation_loss_m": round(self.total_elevation_loss_m, 2),
            "max_slope_deg": round(self.max_slope_deg, 2),
            "avg_slope_deg": round(self.avg_slope_deg, 2),
            "estimated_risk_score": round(self.estimated_risk_score, 1),
            "total_cost": round(self.total_cost, 2),
            "estimated_traverse_time_hr": round(self.estimated_traverse_time_hr, 2),
            "nodes_explored": self.nodes_explored,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "waypoint_count": len(self.waypoints),
            "waypoints": [w.to_dict() for w in self.waypoints],
            "path_grid": self.path_grid,
            "warnings": self.warnings,
            "limitations": self.limitations,
        }

    def to_geojson(self) -> Dict[str, Any]:
        """Convert path to standard GeoJSON Feature for OpenLayers rendering (Developer A)."""
        if not self.found or not self.waypoints:
            return {
                "type": "FeatureCollection",
                "features": [],
                "properties": {"found": False, "status": self.status},
            }

        # Coordinates for LineString: [longitude, latitude, elevation]
        coordinates: List[List[float]] = []
        for wp in self.waypoints:
            if wp.lon is not None and wp.lat is not None:
                coord = [wp.lon, wp.lat]
                if wp.elevation_m is not None:
                    coord.append(wp.elevation_m)
                coordinates.append(coord)
            else:
                # Fallback to grid coordinates if lon/lat not mapped
                coord = [float(wp.grid_x), float(wp.grid_y)]
                coordinates.append(coord)

        line_feature = {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coordinates},
            "properties": {
                "profile": self.profile,
                "total_distance_m": round(self.total_distance_m, 2),
                "estimated_risk_score": round(self.estimated_risk_score, 1),
                "max_slope_deg": round(self.max_slope_deg, 2),
                "avg_slope_deg": round(self.avg_slope_deg, 2),
                "total_cost": round(self.total_cost, 2),
                "traverse_time_hr": round(self.estimated_traverse_time_hr, 2),
                "status": self.status,
            },
        }

        # Waypoint Point features for start, key turns, and goal
        features: List[Dict[str, Any]] = [line_feature]
        for wp in self.waypoints:
            # Include start, goal, and every 10th waypoint or high-risk waypoints
            is_endpoint = wp.step_index == 0 or wp.step_index == len(self.waypoints) - 1
            if is_endpoint or wp.step_index % 10 == 0:
                pt_coord = (
                    [wp.lon, wp.lat]
                    if (wp.lon is not None and wp.lat is not None)
                    else [float(wp.grid_x), float(wp.grid_y)]
                )
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": pt_coord},
                        "properties": {
                            "step_index": wp.step_index,
                            "type": "start"
                            if wp.step_index == 0
                            else ("goal" if is_endpoint else "waypoint"),
                            "elevation_m": wp.elevation_m,
                            "slope_deg": wp.slope_deg,
                            "risk_score": wp.risk_score,
                            "cumulative_distance_m": round(
                                wp.cumulative_distance_m, 1
                            ),
                        },
                    }
                )

        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "profile": self.profile,
                "total_distance_m": round(self.total_distance_m, 2),
                "estimated_risk_score": round(self.estimated_risk_score, 1),
                "max_slope_deg": round(self.max_slope_deg, 2),
                "limitations": self.limitations,
            },
        }


@dataclass
class MultiRouteResult:
    """Collection of primary and alternative planned routes."""

    primary: PathResult
    alternatives: List[PathResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        all_routes = [self.primary] + self.alternatives
        comparison = []
        for r in all_routes:
            comparison.append(
                {
                    "profile": r.profile,
                    "found": r.found,
                    "distance_m": round(r.total_distance_m, 2),
                    "estimated_risk_score": round(r.estimated_risk_score, 1),
                    "max_slope_deg": round(r.max_slope_deg, 2),
                    "avg_slope_deg": round(r.avg_slope_deg, 2),
                    "traverse_time_hr": round(r.estimated_traverse_time_hr, 2),
                    "total_cost": round(r.total_cost, 2),
                }
            )

        return {
            "primary": self.primary.to_dict(),
            "alternatives": [alt.to_dict() for alt in self.alternatives],
            "comparison": comparison,
            "limitations": self.primary.limitations,
        }

    def to_geojson(self) -> Dict[str, Any]:
        """Combine all routes into a single GeoJSON FeatureCollection."""
        features = []
        for route in [self.primary] + self.alternatives:
            geo = route.to_geojson()
            features.extend(geo.get("features", []))

        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "route_count": 1 + len(self.alternatives),
                "limitations": self.primary.limitations,
            },
        }
