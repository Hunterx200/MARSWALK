"""Region schema definitions."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.common import BoundingBox


class DataCoverage(BaseModel):
    imagery: Literal["available", "partial", "unavailable"]
    topography: Literal["available", "partial", "unavailable"]
    observations: Literal["available", "partial", "unavailable"]


class RegionItem(BaseModel):
    id: str
    name: str
    description: str
    bbox: BoundingBox
    crs: str = "EPSG:4326"
    data_coverage: DataCoverage
    sources: List[str] = Field(default_factory=list)

    # Frontend convenience fields (matches frontend/src/types/api.ts)
    target_body: Optional[str] = "Mars"
    center: Optional[Dict[str, float]] = None
    bounds: Optional[BoundingBox] = None
    elevation_range_m: Optional[Dict[str, Any]] = None
    primary_mission: Optional[str] = None
    landing_site: Optional[Dict[str, Any]] = None


class RegionsResponse(BaseModel):
    regions: List[RegionItem]
