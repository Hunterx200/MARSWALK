"""Observation schema definitions."""
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
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

    # Frontend convenience fields (matches frontend/src/types/api.ts)
    target_name: Optional[str] = None
    feature_type: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    elevation_m: Optional[float] = None
    scientific_value: Optional[str] = None
    instruments: Optional[List[str]] = None
    nasa_pds_reference: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_frontend_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "title" in data and "target_name" not in data:
                data["target_name"] = data["title"]
            if "latitude" in data and "lat" not in data:
                data["lat"] = data["latitude"]
            if "longitude" in data and "lon" not in data:
                data["lon"] = data["longitude"]
            if "type" in data and "feature_type" not in data:
                data["feature_type"] = "landing_site" if "landing" in data.get("title", "").lower() else "science_target"
        return data


class ObservationsResponse(BaseModel):
    region_id: str
    count: int
    observations: List[ObservationItem] = Field(default_factory=list)
