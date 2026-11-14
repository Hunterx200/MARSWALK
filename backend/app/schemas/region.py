"""Region schema definitions."""
from typing import List, Literal
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


class RegionsResponse(BaseModel):
    regions: List[RegionItem]
