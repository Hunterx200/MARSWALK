"""Map layers endpoint."""
from fastapi import APIRouter, Query
from app.schemas.layer import LayersResponse
from app.services.nasa_trek import nasa_trek_service

router = APIRouter(tags=["Layers"])


@router.get("/layers", response_model=LayersResponse)
async def get_layers(region_id: str = Query(default="jezero_crater")):
    """
    Get map layers for a region.
    Returns only layers whose WMTS capabilities have been verified.
    Unreachable or unverified layers are explicitly labeled as unavailable with null URL.
    """
    layers = await nasa_trek_service.get_layers(region_id=region_id)
    return LayersResponse(
        region_id=region_id,
        layers=layers,
    )
