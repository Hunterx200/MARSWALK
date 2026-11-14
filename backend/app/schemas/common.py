"""Common Pydantic models for MARSWALK backend."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class GeoCoordinate(BaseModel):
    """Mars geographic coordinates in degrees (supports both longitude/latitude and lon/lat)."""
    longitude: float = Field(default=0.0, description="Mars geographic longitude in degrees")
    latitude: float = Field(default=0.0, description="Mars geographic latitude in degrees")
    lon: Optional[float] = None
    lat: Optional[float] = None
    name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_coords(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map lon -> longitude
            if "lon" in data and "longitude" not in data:
                data["longitude"] = data["lon"]
            elif "longitude" in data and "lon" not in data:
                data["lon"] = data["longitude"]

            # Map lat -> latitude
            if "lat" in data and "latitude" not in data:
                data["latitude"] = data["lat"]
            elif "latitude" in data and "lat" not in data:
                data["lat"] = data["latitude"]
        return data


class BoundingBox(BaseModel):
    """Bounding box in Mars geographic degrees."""
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


class ProvenanceMetadata(BaseModel):
    """Provenance and verification tracking metadata."""
    retrieved_at: str
    verification_status: Optional[str] = "verified"
    limitations: List[str] = Field(default_factory=list)
    cost_model: Optional[str] = None
    generated_at: Optional[str] = None
