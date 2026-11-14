"""Common Pydantic models for MARSWALK backend."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class GeoCoordinate(BaseModel):
    """Mars geographic coordinates in degrees."""
    longitude: float = Field(..., description="Mars geographic longitude in degrees (-180 to 180 or 0 to 360)")
    latitude: float = Field(..., description="Mars geographic latitude in degrees (-90 to 90)")


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
