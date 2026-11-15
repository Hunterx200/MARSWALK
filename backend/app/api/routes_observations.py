"""Observations endpoint."""
from typing import Optional
from fastapi import APIRouter, Query
from app.schemas.observation import ObservationsResponse
from app.services.nasa_pds import nasa_pds_service

router = APIRouter(tags=["Observations"])


@router.get("/observations", response_model=ObservationsResponse)
async def get_observations(
    region_id: str = Query(default="jezero_crater"),
    limit: int = Query(default=50, ge=1, le=200),
    source: Optional[str] = Query(default=None),
):
    """
    Retrieve observations and science targets for Jezero Crater.
    Explicitly distinguishes live verified NASA PDS records from simulated demonstration observations.
    """
    obs_list = await nasa_pds_service.get_observations(
        region_id=region_id,
        limit=limit,
        source_filter=source,
    )
    return ObservationsResponse(
        region_id=region_id,
        count=len(obs_list),
        observations=obs_list,
    )
