"""Terrain schema definitions."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class GridMeta(BaseModel):
    width: int
    height: int
    cell_size_meters: float
    origin_lon: float
    origin_lat: float
    crs: str = "EPSG:4326"


class ElevationData(BaseModel):
    available: bool
    unit: str = "meters"
    source: str = "NASA MOLA"
    source_url: str
    resolution_meters: float
    values: List[List[float]] = Field(default_factory=list)


class SlopeData(BaseModel):
    available: bool
    unit: str = "degrees"
    method: str = "central difference on elevation grid"
    values: List[List[float]] = Field(default_factory=list)


class RoughnessData(BaseModel):
    available: bool = False
    unit: str = "unitless"
    method: str = "not available in MVP"
    values: List[List[float]] = Field(default_factory=list)


class TerrainProvenance(BaseModel):
    retrieved_at: str
    limitations: List[str] = Field(default_factory=list)


class TerrainResponse(BaseModel):
    region_id: str
    status: Literal["available", "partial", "unavailable"]
    grid: GridMeta
    elevation: ElevationData
    slope: SlopeData
    roughness: RoughnessData
    provenance: TerrainProvenance

    # Frontend convenience fields (matches frontend/src/types/api.ts TerrainSummary)
    sample_resolution_m: Optional[float] = 463.0
    min_elevation_m: Optional[float] = None
    max_elevation_m: Optional[float] = None
    mean_slope_deg: Optional[float] = None
    max_slope_deg: Optional[float] = None
    roughness_index: Optional[float] = None
    data_coverage_percent: Optional[float] = None
    source_dataset: Optional[str] = "NASA MGS MOLA MEGDR 128ppd"
    disclaimer: Optional[str] = "Terrain slopes derived from NASA MGS MOLA MEGDR topography. Research prototype."
