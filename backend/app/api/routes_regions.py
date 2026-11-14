"""Region metadata endpoints."""
from fastapi import APIRouter
from app.config import settings
from app.schemas.common import BoundingBox
from app.schemas.region import RegionsResponse, RegionItem, DataCoverage
from app.services.terrain_service import terrain_service

router = APIRouter(tags=["Regions"])


@router.get("/regions", response_model=RegionsResponse)
async def get_regions():
    """List exploration regions and metadata."""
    topo_status = "available" if terrain_service.is_available else "unavailable"

    region = RegionItem(
        id=settings.jezero_id,
        name=settings.jezero_name,
        description=settings.jezero_description,
        bbox=BoundingBox(
            min_lon=settings.min_lon,
            min_lat=settings.min_lat,
            max_lon=settings.max_lon,
            max_lat=settings.max_lat,
        ),
        crs=settings.crs,
        data_coverage=DataCoverage(
            imagery="available",
            topography=topo_status,
            observations="available",
        ),
        sources=[
            "NASA Mars Trek (WMTS)",
            "NASA Mars Global Surveyor (MGS) MOLA MEGDR",
            "NASA Mars 2020 Perseverance Mission Context",
        ],
    )
    return RegionsResponse(regions=[region])
