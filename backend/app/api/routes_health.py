"""Health check endpoint."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

from app.config import settings
from app.core.provenance import get_current_utc_iso
from app.services.nasa_trek import nasa_trek_service
from app.services.nasa_pds import nasa_pds_service

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    time_utc: str
    dependencies: Dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Health check endpoint reporting service status and dependency availability.
    Does not fail if external NASA services are unreachable.
    """
    trek_status = await nasa_trek_service.check_service_health()
    pds_status = await nasa_pds_service.check_service_health()
    
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.version,
        time_utc=get_current_utc_iso(),
        dependencies={
            "nasa_trek": trek_status,
            "nasa_pds": pds_status,
            "route_engine": "available",
        },
    )
