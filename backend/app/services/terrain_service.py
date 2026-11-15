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
                # Compute slope via central differences with anisotropic cell spacing at Jezero latitude (~18.45°N)
                # dy = 3396190 * pi / 180 / 128 = 463.09 m
                # dx = dy * cos(18.45°) = 439.29 m
                dy = 463.09
                dx = 439.29
                gy, gx = np.gradient(self._elevation, dy, dx)
                grad_magnitude = np.sqrt(gx**2 + gy**2)
                self._slope = np.degrees(np.arctan(grad_magnitude))
                logger.info(f"Loaded verified MOLA elevation grid: shape {self._elevation.shape}, min {self._elevation.min()}m, max {self._elevation.max()}m")
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
        Convert Mars geographic coordinates (degrees) to route-grid row and column using PDS pixel-center convention.
        lon(col) = 77.00390625 + col / 128.0
        lat(row) = 18.69921875 - row / 128.0
        """
        h, w = self.get_grid_dimensions()
        col = int(round((lon - 77.00390625) * 128.0))
        row = int(round((18.69921875 - lat) * 128.0))
        # Clamp to full DEM bounds
        col = max(0, min(w - 1, col))
        row = max(0, min(h - 1, row))
        return row, col

    def grid_to_geo(self, row: int, col: int) -> Tuple[float, float]:
        """Convert route-grid row and column to Mars geographic longitude and latitude using PDS pixel-center convention."""
        lon = 77.00390625 + col / 128.0
        lat = 18.69921875 - row / 128.0
        return round(float(lon), 6), round(float(lat), 6)

    def get_elevation_at(self, lon: float, lat: float) -> float:
        """
        Bilinear interpolation across DEM with margin fallback.
        Guarantees zero IndexError across all coordinates in DEM footprint [-0.5, 102.5] x [-0.5, 64.5].
        Raises ValueError for coordinates outside DEM footprint.
        """
        if not self.is_available or self._elevation is None:
            raise ValueError("Elevation dataset is unavailable.")

        u = (lon - 77.00390625) * 128.0
        v = (18.69921875 - lat) * 128.0

        # Validate against DEM footprint boundaries
        if not (-0.5 <= u <= 102.5 and -0.5 <= v <= 64.5):
            raise ValueError(f"Coordinate ({lon:.6f}°E, {lat:.6f}°N) is outside the DEM footprint.")

        # Standard 4-point bilinear interpolation inside interior: 0.0 <= u < 102.0 and 0.0 <= v < 64.0
        if 0.0 <= u < 102.0 and 0.0 <= v < 64.0:
            c0 = int(u)
            c1 = c0 + 1
            r0 = int(v)
            r1 = r0 + 1
            du = u - c0
            dv = v - r0
            z00 = self._elevation[r0, c0]
            z01 = self._elevation[r0, c1]
            z10 = self._elevation[r1, c0]
            z11 = self._elevation[r1, c1]
            top = z00 * (1.0 - du) + z01 * du
            bot = z10 * (1.0 - du) + z11 * du
            return float(top * (1.0 - dv) + bot * dv)

        # Boundary margin fallback: nearest discrete cell center (avoids out-of-bounds c1=103 or r1=65)
        c = max(0, min(102, int(round(u))))
        r = max(0, min(64, int(round(v))))
        return float(self._elevation[r, c])

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
                source_url="https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt44n000hb.lbl",
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
