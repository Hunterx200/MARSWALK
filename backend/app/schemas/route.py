"""Route schema definitions."""
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator
from app.schemas.common import GeoCoordinate


class RouteOptions(BaseModel):
    max_slope_degrees: float = Field(default=25.0, ge=0.0, le=90.0)
    avoid_hazards: bool = True
    hazard_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    slope_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    distance_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    alternatives: int = Field(default=2, ge=0, le=5)
    profile: Optional[str] = Field(default="balanced", description="Routing profile: 'balanced', 'direct', or 'safe'")
    allow_diagonal: bool = True


class RoutePlanRequest(BaseModel):
    region_id: str = "jezero_crater"
    start: Optional[GeoCoordinate] = None
    goal: Optional[GeoCoordinate] = None
    options: Optional[RouteOptions] = Field(default_factory=RouteOptions)
    
    # Optional direct grid coordinates for algorithm testing
    start_x: Optional[int] = None
    start_y: Optional[int] = None
    goal_x: Optional[int] = None
    goal_y: Optional[int] = None
    profile: Optional[str] = None
    allow_diagonal: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            opts = data.get("options") or {}
            if "profile" in data and "profile" not in opts:
                opts["profile"] = data["profile"]
            if "allow_diagonal" in data and "allow_diagonal" not in opts:
                opts["allow_diagonal"] = data["allow_diagonal"]
            data["options"] = opts
        return data


class PathNode(BaseModel):
    longitude: float
    latitude: float
    row: int
    column: int


class RouteDataCoverage(BaseModel):
    elevation: Literal["available", "partial", "unavailable"]
    hazards: Literal["available", "partial", "unavailable"]


class RouteProvenance(BaseModel):
    generated_at: str
    cost_model: str = "distance + slope + hazard proximity"
    limitations: List[str] = Field(default_factory=list)


class RouteItem(BaseModel):
    id: str
    label: str
    algorithm: str = "A*"
    profile: Optional[str] = None
    start: GeoCoordinate
    goal: GeoCoordinate
    path: List[PathNode] = Field(default_factory=list)
    distance_meters: float
    estimated_travel_time_minutes: float
    mean_slope_degrees: float
    maximum_slope_degrees: float
    mean_hazard_score: float
    maximum_hazard_score: float
    risk_level: Literal["low", "medium", "high"]
    data_coverage: RouteDataCoverage
    warnings: List[str] = Field(default_factory=list)
    provenance: RouteProvenance
    risk_score: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    elevation_loss_m: Optional[float] = None
    total_cost: Optional[float] = None
    waypoint_count: Optional[int] = None


class RoutePlanResponse(BaseModel):
    request_id: str
    region_id: str
    status: Literal["success", "partial", "failed"]
    routes: List[RouteItem] = Field(default_factory=list)
    message: str = "Route is a planning estimate and is not guaranteed safe."
    geojson: Optional[Dict[str, Any]] = None
    comparison: Optional[List[Dict[str, Any]]] = None
