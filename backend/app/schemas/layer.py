"""Map layer schema definitions."""
from typing import Any, List, Literal, Optional, Union
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

    # Frontend convenience fields (matches frontend/src/types/api.ts)
    visible: Optional[bool] = True
    opacity: Optional[float] = 1.0
    category: Optional[str] = "basemap"
    description: Optional[str] = None
    verified_nasa_source: Optional[bool] = True


class LayersResponse(BaseModel):
    region_id: str
    layers: List[MapLayer]
