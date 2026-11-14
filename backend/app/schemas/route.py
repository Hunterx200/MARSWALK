"""Route schema definitions."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.common import GeoCoordinate


class RouteOptions(BaseModel):
    max_slope_degrees: float = Field(default=25.0, ge=0.0, le=90.0)
    avoid_hazards: bool = True
    hazard_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    slope_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    distance_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    alternatives: int = Field(default=0, ge=0, le=5)


class RoutePlanRequest(BaseModel):
    region_id: str = "jezero_crater"
    start: GeoCoordinate
    goal: GeoCoordinate
    options: Optional[RouteOptions] = Field(default_factory=RouteOptions)


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


class RoutePlanResponse(BaseModel):
    request_id: str
    region_id: str
    status: Literal["success", "partial", "failed"]
    routes: List[RouteItem] = Field(default_factory=list)
    message: str = "Route is a planning estimate and is not guaranteed safe."
