"""Observation schema definitions."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.common import ProvenanceMetadata


class ObservationItem(BaseModel):
    id: str
    title: str
    type: Literal["rover_observation", "imagery", "science_target", "other"]
    longitude: float
    latitude: float
    sol: Optional[int] = None
    acquired_at: Optional[str] = None
    source: str
    source_url: str
    dataset_id: Optional[str] = None
    description: str
    thumbnail_url: Optional[str] = None
    provenance: ProvenanceMetadata


class ObservationsResponse(BaseModel):
    region_id: str
    count: int
    observations: List[ObservationItem] = Field(default_factory=list)
