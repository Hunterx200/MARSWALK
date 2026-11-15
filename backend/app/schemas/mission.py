"""Mission schema definitions."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class MissionSummary(BaseModel):
    distance_meters: float
    risk_level: Literal["low", "medium", "high"]
    mean_slope_degrees: float
    maximum_slope_degrees: float
    hazard_score: float
    observations: int = 0


class MissionSection(BaseModel):
    title: str
    content: str


class MissionReport(BaseModel):
    title: str = "MARSWALK Mission Plan"
    sections: List[MissionSection] = Field(default_factory=list)


class MissionCreateRequest(BaseModel):
    region_id: str = "jezero_crater"
    name: str = Field(..., min_length=1, max_length=120)
    route_id: str
    notes: Optional[str] = None


class MissionResponse(BaseModel):
    id: str
    name: str
    region_id: str
    route_id: str
    created_at: str
    status: str = "draft"
    summary: MissionSummary
    report: MissionReport
    notes: Optional[str] = None
