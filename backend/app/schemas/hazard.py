"""Hazard schema definitions."""
from typing import List, Literal
from pydantic import BaseModel, Field


class HazardScoreData(BaseModel):
    available: bool
    unit: str = "0-100"
    method: str = "project-generated heuristic"
    values: List[List[float]] = Field(default_factory=list)


class HazardType(BaseModel):
    id: str
    name: str
    basis: str
    confidence: Literal["low", "medium", "high"]
    available: bool


class HazardProvenance(BaseModel):
    retrieved_at: str
    limitations: List[str] = Field(default_factory=list)


class HazardsResponse(BaseModel):
    region_id: str
    status: Literal["available", "partial", "unavailable"]
    hazard_score: HazardScoreData
    hazard_types: List[HazardType] = Field(default_factory=list)
    provenance: HazardProvenance
