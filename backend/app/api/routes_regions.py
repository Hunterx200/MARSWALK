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

    bbox = BoundingBox(
        min_lon=settings.min_lon,
        min_lat=settings.min_lat,
        max_lon=settings.max_lon,
        max_lat=settings.max_lat,
    )

    region = RegionItem(
        id=settings.jezero_id,
        name=settings.jezero_name,
        description=settings.jezero_description,
        bbox=bbox,
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
        target_body="Mars",
        center={"lat": 18.4447, "lon": 77.4508},
        bounds=bbox,
        elevation_range_m={
            "min": -2719.0,
            "max": -1537.0,
            "datum": "Mars MOLA Geoid (areoid)",
        },
        primary_mission="Mars 2020 (Perseverance Rover)",
        landing_site={
            "name": "Octavia E. Butler Landing",
            "lat": 18.4447,
            "lon": 77.4508,
            "sol_0_date": "2021-02-18",
        },
    )
    return RegionsResponse(regions=[region])
