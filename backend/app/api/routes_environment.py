"""FastAPI router for Perseverance MEDA Environmental Intelligence endpoints."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Query, Path

from app.schemas.environment import (
    MEDASolTelemetryResponse,
    MEDASolSummaryResponse,
    MEDASolTimeSeriesResponse,
)
from app.services.meda_service import meda_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/environment", tags=["Environmental Intelligence"])


@router.get("/sols", response_model=List[int], summary="Get list of available Sols")
async def get_available_sols():
    """Return all Sols with verified historical MEDA telemetry archived in the system."""
    return meda_service.get_available_sols()


@router.get("/telemetry", response_model=MEDASolTelemetryResponse, summary="Get MEDA telemetry snapshot")
async def get_meda_telemetry(
    sol: int = Query(755, ge=0, description="Martian Sol number"),
    sclk: Optional[float] = Query(None, description="Optional target Spacecraft Clock timestamp")
):
    """
    Retrieve historical Perseverance MEDA multi-sensor telemetry for a specific Sol.
    
    If sclk is omitted, a representative midday observation snapshot is returned.
    All data is backed by official NASA PDS4 archive tables.
    """
    return meda_service.get_sol_telemetry(sol=sol, requested_sclk=sclk)


@router.get("/summary", response_model=MEDASolSummaryResponse, summary="Get Sol summary statistics")
async def get_sol_summary(
    sol: int = Query(755, ge=0, description="Martian Sol number")
):
    """
    Retrieve verified environmental summary statistics across an entire Sol.
    
    Includes min/max/mean observations, valid counts, and individual sensor operational status.
    """
    return meda_service.get_sol_summary(sol=sol)


@router.get("/timeseries", response_model=MEDASolTimeSeriesResponse, summary="Get Sol time-series")
async def get_sol_timeseries(
    sol: int = Query(755, ge=0, description="Martian Sol number"),
    max_points: int = Query(100, ge=10, le=500, description="Maximum number of sampled points")
):
    """
    Retrieve a uniformly sampled diurnal time series for chart visualizations.
    
    Preserves native data fidelity without cross-sensor time interpolation.
    """
    return meda_service.get_sol_timeseries(sol=sol, max_points=max_points)

