"""Map layer schema definitions."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.common import BoundingBox


class MapLayer(BaseModel):
    id: str
    name: str
    type: str = "wmts"
    status: Literal["available", "unavailable"]
    url: Optional[str] = None
    attribution: str
    source_url: str
    coverage: BoundingBox
    limitations: List[str] = Field(default_factory=list)


class LayersResponse(BaseModel):
    region_id: str
    layers: List[MapLayer]
