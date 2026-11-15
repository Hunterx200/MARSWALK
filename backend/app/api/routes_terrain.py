"""Terrain endpoint."""
from typing import Optional
from fastapi import APIRouter, Query
from app.schemas.terrain import TerrainResponse
from app.services.terrain_service import terrain_service

router = APIRouter(tags=["Terrain"])


@router.get("/terrain", response_model=TerrainResponse)
async def get_terrain(
    region_id: str = Query(default="jezero_crater"),
    min_lon: Optional[float] = Query(default=None),
    min_lat: Optional[float] = Query(default=None),
    max_lon: Optional[float] = Query(default=None),
    max_lat: Optional[float] = Query(default=None),
    resolution: str = Query(default="coarse"),
):
    """
    Retrieve terrain elevation grid and derived slope data for Jezero Crater.
    Backed by NASA MGS MOLA MEGDR topography at ~463 m resolution.
    Does not fabricate data if unavailable.
    """
    return terrain_service.get_terrain_response(region_id=region_id)
