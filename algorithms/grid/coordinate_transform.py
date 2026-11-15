"""Mars Geographic to Grid Coordinate Transformation for Jezero Crater.

Converts between Mars geographic coordinates (Longitude East, Latitude North)
and discrete 2D raster grid coordinates (column, row).

Semantics & Reference:
- Mars Mean Spherical Radius: 3,389,500 meters (IAU 2000 Mars sphere)
- Jezero Crater Center: ~77.45°E, ~18.38°N
- Grid Origin (0, 0): Top-Left (North-West) corner of the raster
- x increases Eastward (columns 0 .. width - 1)
- y increases Southward (rows 0 .. height - 1)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from algorithms.models import GridCoordinate, GridSpec, MarsCoordinate


# Mars Mean Radius according to IAU 2000
MARS_RADIUS_METERS = 3389500.0


def create_jezero_default_grid_spec(
    width: int = 100,
    height: int = 100,
    resolution_m: float = 10.0,
    center_lon: float = 77.45,
    center_lat: float = 18.38,
) -> GridSpec:
    """Create a standard GridSpec centered on Jezero Crater Western Fan.

    Args:
        width: Grid width in cells (columns).
        height: Grid height in cells (rows).
        resolution_m: Ground sampling distance in meters per cell (default 10m).
        center_lon: Center longitude in degrees East.
        center_lat: Center latitude in degrees North.

    Returns:
        GridSpec covering the area around the center.
    """
    # Calculate degree spans
    # Meters per degree latitude: R * pi / 180
    m_per_deg_lat = MARS_RADIUS_METERS * (math.pi / 180.0)
    # Meters per degree longitude at center_lat: R * cos(lat) * pi / 180
    m_per_deg_lon = MARS_RADIUS_METERS * math.cos(math.radians(center_lat)) * (math.pi / 180.0)

    total_width_m = width * resolution_m
    total_height_m = height * resolution_m

    d_lon = total_width_m / m_per_deg_lon
    d_lat = total_height_m / m_per_deg_lat

    lon_min = center_lon - d_lon / 2.0
    lon_max = center_lon + d_lon / 2.0
    lat_min = center_lat - d_lat / 2.0
    lat_max = center_lat + d_lat / 2.0

    return GridSpec(
        width=width,
        height=height,
        resolution_m=resolution_m,
        lon_min=lon_min,
        lat_min=lat_min,
        lon_max=lon_max,
        lat_max=lat_max,
        crs="Mars 2000 / Equirectangular",
        description="Jezero Crater Western Delta Fan Region",
    )


class JezeroCoordinateTransformer:
    """Bidirectional transformer between Mars Lon/Lat and Raster Grid coords."""

    def __init__(self, spec: GridSpec) -> None:
        self.spec = spec
        self.width = spec.width
        self.height = spec.height
        self.resolution_m = spec.resolution_m

        self.lon_min = spec.lon_min
        self.lon_max = spec.lon_max
        self.lat_min = spec.lat_min
        self.lat_max = spec.lat_max

        self.lon_span = self.lon_max - self.lon_min
        self.lat_span = self.lat_max - self.lat_min

        if self.lon_span <= 0 or self.lat_span <= 0:
            raise ValueError(f"Invalid bounding box: lon [{self.lon_min}..{self.lon_max}], lat [{self.lat_min}..{self.lat_max}]")

    def mars_to_grid(self, lon: float, lat: float) -> Tuple[int, int]:
        """Convert Mars geographic coordinates (lon East, lat North) to grid (x, y).

        Note:
        - x increases Eastward: 0 at lon_min, width - 1 at lon_max.
        - y increases Southward: 0 at lat_max (North), height - 1 at lat_min (South).
        """
        # Normalized coordinates [0.0, 1.0]
        u = (lon - self.lon_min) / self.lon_span
        # Invert latitude because row 0 is at the North (lat_max)
        v = (self.lat_max - lat) / self.lat_span

        grid_x = int(round(u * (self.width - 1)))
        grid_y = int(round(v * (self.height - 1)))

        return (grid_x, grid_y)

    def grid_to_mars(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convert discrete grid cell (x, y) to Mars geographic coordinates (lon, lat).

        Returns:
            Tuple of (lon_east_deg, lat_north_deg).
        """
        u = float(grid_x) / max(1, self.width - 1)
        v = float(grid_y) / max(1, self.height - 1)

        lon = self.lon_min + u * self.lon_span
        lat = self.lat_max - v * self.lat_span

        return (round(lon, 6), round(lat, 6))

    def is_mars_coord_in_bounds(self, lon: float, lat: float) -> bool:
        """Check if geographic coordinate falls within grid extent."""
        return (self.lon_min <= lon <= self.lon_max) and (self.lat_min <= lat <= self.lat_max)

    def is_grid_coord_in_bounds(self, x: int, y: int) -> bool:
        """Check if grid cell is within array dimensions."""
        return 0 <= x < self.width and 0 <= y < self.height
