"""Terrain service managing Jezero Crater elevation and slope grids."""
import os
import logging
from typing import Optional, Tuple
import numpy as np

from app.config import settings
from app.core.provenance import get_current_utc_iso, MOLA_TERRAIN_LIMITATIONS
from app.schemas.terrain import (
    GridMeta,
    ElevationData,
    SlopeData,
    RoughnessData,
    TerrainProvenance,
    TerrainResponse,
)

logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jezero_mola_128ppd.npy")


class TerrainService:
    def __init__(self, data_file_path: str = DATA_PATH):
        self.data_file_path = data_file_path
        self._elevation: Optional[np.ndarray] = None
        self._slope: Optional[np.ndarray] = None
        self._load_data()

    def _load_data(self):
        """Load pre-extracted verified NASA MOLA 128ppd MEGDR slice if available."""
        if os.path.exists(self.data_file_path):
            try:
                arr = np.load(self.data_file_path)
                # Ensure 2D float array
                self._elevation = arr.astype(float)
                # Compute slope via central differences on elevation grid
                # Cell size is ~463.0 meters on Mars equator/sub-tropics (3389.5 km * pi / 180 / 128 ~ 462.1m)
                cell_size_m = 463.0
                gy, gx = np.gradient(self._elevation, cell_size_m)
                grad_magnitude = np.sqrt(gx**2 + gy**2)
                self._slope = np.degrees(np.arctan(grad_magnitude))
                logger.info(f"Loaded verified MOLA elevation grid: shape {self._elevation.shape}")
            except Exception as e:
                logger.error(f"Failed to load elevation grid from {self.data_file_path}: {e}")
                self._elevation = None
                self._slope = None
        else:
            logger.warning(f"No elevation dataset found at {self.data_file_path}. Data marked unavailable.")
            self._elevation = None
            self._slope = None

    @property
    def is_available(self) -> bool:
        return self._elevation is not None and self._slope is not None

    def get_grid_dimensions(self) -> Tuple[int, int]:
        """Return (height, width) as row count, col count."""
        if self._elevation is not None:
            return self._elevation.shape[0], self._elevation.shape[1]
        return 65, 103

    def geo_to_grid(self, lon: float, lat: float) -> Tuple[int, int]:
        """
        Convert Mars geographic coordinates (degrees) to route-grid row and column.
        Row 0 is northern boundary (max_lat 18.7), Row (H-1) is southern boundary (min_lat 18.2).
        Col 0 is western boundary (min_lon 77.0), Col (W-1) is eastern boundary (max_lon 77.8).
        """
        h, w = self.get_grid_dimensions()
        col = int(round((lon - settings.min_lon) / (settings.max_lon - settings.min_lon) * (w - 1)))
        row = int(round((settings.max_lat - lat) / (settings.max_lat - settings.min_lat) * (h - 1)))
        # Clamp to grid bounds
        col = max(0, min(w - 1, col))
        row = max(0, min(h - 1, row))
        return row, col

    def grid_to_geo(self, row: int, col: int) -> Tuple[float, float]:
        """Convert route-grid row and column to Mars geographic longitude and latitude."""
        h, w = self.get_grid_dimensions()
        lon = settings.min_lon + (col / (w - 1)) * (settings.max_lon - settings.min_lon)
        lat = settings.max_lat - (row / (h - 1)) * (settings.max_lat - settings.min_lat)
        return round(float(lon), 5), round(float(lat), 5)

    def get_terrain_response(self, region_id: str = "jezero_crater") -> TerrainResponse:
        """Construct standard TerrainResponse object adhering strictly to API contract."""
        now_iso = get_current_utc_iso()
        h, w = self.get_grid_dimensions()
        
        grid_meta = GridMeta(
            width=w,
            height=h,
            cell_size_meters=463.0,
            origin_lon=settings.min_lon,
            origin_lat=settings.min_lat,
            crs=settings.crs,
        )

        if not self.is_available:
            return TerrainResponse(
                region_id=region_id,
                status="unavailable",
                grid=grid_meta,
                elevation=ElevationData(
                    available=False,
                    unit="meters",
                    source="NASA MOLA",
                    source_url="https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/",
                    resolution_meters=463.0,
                    values=[],
                ),
                slope=SlopeData(
                    available=False,
                    unit="degrees",
                    method="central difference on elevation grid",
                    values=[],
                ),
                roughness=RoughnessData(
                    available=False,
                    unit="unitless",
                    method="not available in MVP",
                    values=[],
                ),
                provenance=TerrainProvenance(
                    retrieved_at=now_iso,
                    limitations=MOLA_TERRAIN_LIMITATIONS + ["Elevation dataset is currently offline or unavailable."],
                ),
            )

        # Elevation and slope values as list of lists (rounded to 1 decimal place)
        elev_list = np.round(self._elevation, 1).tolist()
        slope_list = np.round(self._slope, 2).tolist()

        return TerrainResponse(
            region_id=region_id,
            status="available",
            grid=grid_meta,
            elevation=ElevationData(
                available=True,
                unit="meters",
                source="NASA MOLA",
                source_url="https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt00n000hb.lbl",
                resolution_meters=463.0,
                values=elev_list,
            ),
            slope=SlopeData(
                available=True,
                unit="degrees",
                method="central difference on elevation grid",
                values=slope_list,
            ),
            roughness=RoughnessData(
                available=False,
                unit="unitless",
                method="not available in MVP",
                values=[],
            ),
            provenance=TerrainProvenance(
                retrieved_at=now_iso,
                limitations=MOLA_TERRAIN_LIMITATIONS,
            ),
        )


terrain_service = TerrainService()
