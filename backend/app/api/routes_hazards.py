"""Hazards endpoint."""
from typing import Optional
from fastapi import APIRouter, Query
from app.schemas.hazard import HazardsResponse
from app.services.hazard_service import hazard_service

router = APIRouter(tags=["Hazards"])


@router.get("/hazards", response_model=HazardsResponse)
async def get_hazards(
    region_id: str = Query(default="jezero_crater"),
    min_lon: Optional[float] = Query(default=None),
    min_lat: Optional[float] = Query(default=None),
    max_lon: Optional[float] = Query(default=None),
    max_lat: Optional[float] = Query(default=None),
):
    """
    Retrieve project-generated hazard grid for Jezero Crater.
    Derives steep-slope hazards directly from MOLA topography gradients.
    """
    return hazard_service.get_hazards_response(region_id=region_id)
