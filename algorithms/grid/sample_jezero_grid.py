"""Documented Sample Benchmark Grid for Jezero Crater Western Delta.

PROVENANCE NOTICE:
This dataset is a documented SYNTHETIC BENCHMARK MODEL modeled after published
topographic characteristics of the Jezero Crater Western Fan (Mars 2020 landing site).
It is explicitly designated for algorithmic testing, integration, and UI verification.
It is NOT raw NASA orbital telemetry. When raw HiRISE or MOLA GeoTIFF rasters are
ingested, they replace this benchmark dataset.

Features modeled:
- Western Delta deposit: elevated terrace (-2250m)
- Crater floor basin (-2500m baseline)
- Delta front scarp: steep slopes (20° to 35°)
- Isolated residual butte: "Kodiak Butte"
- Hazardous sand dune fields (e.g. Séítah ripple hazards)
- Boulder cluster hazard fields
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import numpy as np

from algorithms.grid.coordinate_transform import (
    JezeroCoordinateTransformer,
    create_jezero_default_grid_spec,
)
from algorithms.models import GridSpec
from algorithms.science.observation_planner import ScienceTarget


BENCHMARK_METADATA: Dict[str, Any] = {
    "dataset_name": "Jezero Crater Western Fan Benchmark Grid",
    "provenance": "SYNTHETIC_BENCHMARK_DEM",
    "is_real_nasa_telemetry": False,
    "description": (
        "Documented benchmark model with realistic topographic morphology for Jezero Crater. "
        "Intended for algorithm benchmarking, regression testing, and frontend map integration."
    ),
    "target_region": "Jezero Crater, Mars (approx 77.45°E, 18.38°N)",
    "nominal_elevation_range_m": [-2530.0, -2220.0],
    "known_limitations": [
        "Synthetic benchmark for testing; does not represent exact current rover position.",
        "Local sub-meter rocks and micro-dune slip are not represented.",
        "Replace with verified NASA HiRISE/MOLA GeoTIFF rasters in production pipeline.",
    ],
}


def create_sample_jezero_dataset(
    width: int = 100,
    height: int = 100,
    resolution_m: float = 10.0,
) -> Dict[str, Any]:
    """Generate the documented synthetic benchmark dataset for Jezero Crater.

    Args:
        width: Number of columns (cells east-west). Default 100 cells = 1000m.
        height: Number of rows (cells north-south). Default 100 cells = 1000m.
        resolution_m: Cell size in meters. Default 10.0m.

    Returns:
        Dict containing:
        - 'dem': 2D np.ndarray (float) of elevation in meters
        - 'hazard_mask': 2D np.ndarray (bool) of identified hazards
        - 'grid_spec': GridSpec object
        - 'transformer': JezeroCoordinateTransformer
        - 'science_targets': List[ScienceTarget]
        - 'metadata': Dict[str, Any] provenance and limitation statements
    """
    grid_spec = create_jezero_default_grid_spec(
        width=width,
        height=height,
        resolution_m=resolution_m,
        center_lon=77.45,
        center_lat=18.38,
    )
    transformer = JezeroCoordinateTransformer(grid_spec)

    # Coordinate grids: X (0..width-1), Y (0..height-1)
    # Origin is top-left (NW)
    x = np.arange(width)
    y = np.arange(height)
    xx, yy = np.meshgrid(x, y)

    # 1. Base Crater Floor Topography (gently sloping from -2510m to -2490m)
    # Floor dips slightly toward east-southeast
    base_floor = -2500.0 + 0.1 * (xx - width / 2.0) - 0.05 * (yy - height / 2.0)

    # 2. Western Delta Fan:
    # A raised delta deposit occupying the western region (xx < 35), rising ~100m to -2400m.
    # Ancient inlet channel breach (Neretva Vallis breach at y ~ 20)
    # Shifting the scarp position at y ~ 20 creates a natural inlet canyon / traversable ramp (~12-14 deg)
    ramp_y = 20.0
    ramp_channel = 15.0 * np.exp(-((yy - ramp_y) / 8.0) ** 2)
    scarp_x = 35.0 + ramp_channel
    fan_step = 100.0  # meters
    sigmoid_fan = fan_step / (1.0 + np.exp((xx - scarp_x) / 9.0))
    dem = base_floor + sigmoid_fan

    # 3. Kodiak Butte:
    # An isolated residual remnant mesa at approx grid (x=60, y=70)
    butte_x, butte_y = 60.0, 70.0
    dist_to_butte = np.hypot(xx - butte_x, yy - butte_y)
    butte_radius = 8.0
    butte_height = 140.0
    butte_profile = np.maximum(0.0, 1.0 - (dist_to_butte / butte_radius) ** 2)
    dem += butte_height * butte_profile

    # 4. Small Crater Depression ("Belva Satellite Crater") at grid (x=75, y=25)
    crater_x, crater_y = 75.0, 25.0
    dist_to_crater = np.hypot(xx - crater_x, yy - crater_y)
    crater_radius = 10.0
    crater_depth = 35.0
    crater_profile = np.maximum(0.0, 1.0 - (dist_to_crater / crater_radius) ** 2)
    dem -= crater_depth * crater_profile

    # 5. Natural surface regolith micro-texture (sub-meter variation)
    # Using fixed seed for deterministic reproducibility across tests
    rng = np.random.RandomState(42)
    noise = rng.normal(loc=0.0, scale=0.3, size=(height, width))
    dem += noise

    # -------------------------------------------------------------
    # Hazard Mask Construction (True = Obstacle / High Risk Hazard)
    # -------------------------------------------------------------
    hazard_mask = np.zeros((height, width), dtype=bool)

    # Hazard 1: "Séítah Sand Ripple Field" (high rover wheel slip risk)
    # Region between x in [45, 55] and y in [40, 60]
    seitah_mask = (xx >= 46) & (xx <= 54) & (yy >= 42) & (yy <= 58)
    hazard_mask[seitah_mask] = True

    # Hazard 2: Boulder Field near crater ejecta at (x=70..76, y=18..24)
    boulder_field = (xx >= 70) & (xx <= 76) & (yy >= 18) & (yy <= 24)
    hazard_mask[boulder_field] = True

    # Hazard 3: Kodiak Butte cliff summit keep-out (x=59..61, y=69..71)
    butte_cliff = dist_to_butte <= 4.0
    hazard_mask[butte_cliff] = True

    # -------------------------------------------------------------
    # Science Targets of Interest (POIs) in Jezero
    # -------------------------------------------------------------
    targets_def = [
        (
            "SCI-01",
            "Kodiak Butte Base",
            "stratified_outcrop",
            60,
            62,
            5.0,
            "Key stratigraphy revealing delta depositional sequences.",
        ),
        (
            "SCI-02",
            "Delta Front Fan Base",
            "delta_sediment",
            42,
            22,
            4.8,
            "Fine-grained sedimentary rocks with high biosignature preservation potential.",
        ),
        (
            "SCI-03",
            "Three Forks Sample Depot",
            "sample_cache",
            30,
            20,
            4.5,
            "Documented sample tube depot location for Mars Sample Return.",
        ),
        (
            "SCI-04",
            "Crater Floor Olivine Rock",
            "igneous_unit",
            65,
            30,
            3.5,
            "Volcanic/igneous floor unit dating the Jezero basin floor.",
        ),
        (
            "SCI-05",
            "Belva Crater Ejecta Rim",
            "impact_ejecta",
            75,
            25,
            4.0,
            "Deep bedrock excavated by the Belva impact event.",
        ),
    ]

    science_targets: List[ScienceTarget] = []
    for tid, name, ttype, gx, gy, prio, desc in targets_def:
        lon, lat = transformer.grid_to_mars(gx, gy)
        science_targets.append(
            ScienceTarget(
                target_id=tid,
                name=name,
                target_type=ttype,
                grid_x=gx,
                grid_y=gy,
                lon=lon,
                lat=lat,
                scientific_priority=prio,
                description=desc,
            )
        )

    return {
        "dem": dem,
        "hazard_mask": hazard_mask,
        "grid_spec": grid_spec,
        "transformer": transformer,
        "science_targets": science_targets,
        "metadata": BENCHMARK_METADATA,
    }
