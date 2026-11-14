# MARSWALK — Algorithms Engine (`algorithms/`)

**Author:** Developer C (Algorithms Engineer)  
**Target Region:** Jezero Crater, Mars (~77.45°E, 18.38°N)  
**Subsystem:** Intelligent Surface Route Planning, Terrain Cost Modeling & Hazard Scoring  

---

## 1. Overview & Capabilities

The `algorithms/` module provides a production-grade, mathematically verified navigation planning engine designed for Mars rover exploration across Digital Elevation Models (DEM) and hazard rasters.

### Key Capabilities
- **A\* Pathfinding Engine (`algorithms/routing/astar.py`):**
  - 8-connected grid search with admissible Octile/Euclidean distance heuristics.
  - Corner-cutting prevention (rovers cannot clip diagonally through adjacent obstacle corners).
  - Traversal cost integration (combining slope, roughness, and hazard proximity).
  - Robust failure handling: validates bounds, checks start/goal impassability, and diagnoses unreachable destinations.
- **Terrain Cost Modeling (`algorithms/terrain/`):**
  - 2nd-order central difference slope computation (Horn's method) converting DEM elevation into surface slope angles in degrees.
  - Local surface roughness calculation (standard deviation of elevation).
  - Non-linear slope cost scaling with hard limits (Perseverance threshold ~20°).
- **Hazard Scoring & Proximity (`algorithms/hazards/`):**
  - Exact Euclidean distance transform (`distance_transform_edt`) from detected hazard masks (boulder fields, sand dunes, scarps).
  - Configurable safety buffer zones and hard collision keep-out zones.
  - Standardized composite risk scoring (0.0 to 100.0 scale) combining slope steepness, hazard standoff, and roughness.
- **Alternative Route Generation (`algorithms/routing/alternatives.py`):**
  - Generates three distinct route alternatives: **Direct** (shortest distance), **Balanced** (optimal trade-off), and **Safe** (maximum standoff buffer).
- **Spatial Reference & Coordinates (`algorithms/grid/`):**
  - Strict coordinate semantics separating discrete raster Grid Coordinates (`x=col`, `y=row`) from Mars Geographic Coordinates (`lon=°East`, `lat=°North`).
  - Documented synthetic benchmark dataset for Jezero Crater (`sample_jezero_grid.py`) labeled `SYNTHETIC_BENCHMARK_DEM` for regression testing and UI development.
- **Science Observation Planning (`algorithms/science/`):**
  - Proximity detection and prioritization for scientific points of interest (e.g. Three Forks Sample Depot, Delta Front Outcrops, Kodiak Butte).

---

## 2. Integration Guide for Developer B (Backend / FastAPI)

Developer B owns the FastAPI backend (`backend/`) and exposes `POST /api/routes/plan`.

### FastAPI Endpoint Integration Example

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

from algorithms.routing.alternatives import AlternativeRoutePlanner
from algorithms.models import RouteProfile, RouteRequest
from algorithms.grid.sample_jezero_grid import create_sample_jezero_dataset

router = APIRouter(prefix="/api/routes", tags=["Routes"])

# Initialize planner once at startup with DEM and hazard layers
# (Replace sample dataset with real ingested NASA HiRISE/MOLA GeoTIFF rasters when loaded)
dataset = create_sample_jezero_dataset(width=80, height=80, resolution_m=10.0)
planner = AlternativeRoutePlanner(
    dem=dataset["dem"],
    hazard_mask=dataset["hazard_mask"],
    resolution_m=10.0,
    coord_transformer=dataset["transformer"].grid_to_mars,
)

class RoutePlanRequest(BaseModel):
    start_x: int = Field(..., description="Start grid column x (0..width-1)")
    start_y: int = Field(..., description="Start grid row y (0..height-1)")
    goal_x: int = Field(..., description="Destination grid column x (0..width-1)")
    goal_y: int = Field(..., description="Destination grid row y (0..height-1)")
    profile: Optional[str] = Field("balanced", description="Routing profile: 'balanced', 'direct', or 'safe'")
    allow_diagonal: Optional[bool] = Field(True, description="Enable 8-connected diagonal traverse")

@router.post("/plan")
def plan_route(req: RoutePlanRequest) -> Dict[str, Any]:
    try:
        prof = RouteProfile(req.profile.lower())
    except ValueError:
        prof = RouteProfile.BALANCED

    multi_res = planner.plan_multi_routes(
        start=(req.start_x, req.start_y),
        goal=(req.goal_x, req.goal_y),
        allow_diagonal=req.allow_diagonal,
        preferred_profile=prof,
    )

    # Returns complete JSON structure including GeoJSON for the frontend
    result = multi_res.to_dict()
    result["geojson"] = multi_res.to_geojson()
    return result
```

### JSON Request Schema (`POST /api/routes/plan`)

```json
{
  "start_x": 15,
  "start_y": 20,
  "goal_x": 65,
  "goal_y": 20,
  "profile": "balanced",
  "allow_diagonal": true
}
```

### JSON Response Schema (`POST /api/routes/plan`)

```json
{
  "primary": {
    "found": true,
    "status": "SUCCESS",
    "message": "Optimal balanced route planned successfully.",
    "profile": "balanced",
    "total_distance_m": 500.0,
    "total_elevation_gain_m": 0.0,
    "total_elevation_loss_m": 99.2,
    "max_slope_deg": 16.8,
    "avg_slope_deg": 4.2,
    "estimated_risk_score": 18.5,
    "total_cost": 642.1,
    "estimated_traverse_time_hr": 3.47,
    "nodes_explored": 842,
    "execution_time_ms": 28.5,
    "waypoint_count": 51,
    "waypoints": [
      {
        "step_index": 0,
        "grid_x": 15,
        "grid_y": 20,
        "lon": 77.44558,
        "lat": 18.38334,
        "elevation_m": -2400.8,
        "slope_deg": 1.2,
        "roughness_m": 0.3,
        "hazard_dist_m": 85.0,
        "risk_score": 0.5,
        "cumulative_distance_m": 0.0,
        "segment_cost": 0.0
      }
    ],
    "warnings": [
      "Route traverses steep terrain: maximum slope reaches 16.8°."
    ],
    "limitations": [
      "Project-generated risk estimate. NOT an official NASA safety determination.",
      "Never describe a generated route as guaranteed safe.",
      "Sub-meter obstacles and local sand entrapment cannot be guaranteed detected by orbital data alone."
    ]
  },
  "alternatives": [
    {
      "profile": "direct",
      "found": true,
      "total_distance_m": 500.0,
      "estimated_risk_score": 18.5
    },
    {
      "profile": "safe",
      "found": true,
      "total_distance_m": 500.0,
      "estimated_risk_score": 18.5
    }
  ],
  "comparison": [
    {
      "profile": "balanced",
      "found": true,
      "distance_m": 500.0,
      "estimated_risk_score": 18.5,
      "max_slope_deg": 16.8,
      "avg_slope_deg": 4.2,
      "traverse_time_hr": 3.47,
      "total_cost": 642.1
    }
  ]
}
```

---

## 3. Visualization Format for Developer A (Frontend / OpenLayers)

Developer A can call `multi_res.to_geojson()` or consume the `geojson` field directly in OpenLayers via `ol/format/GeoJSON`.

### GeoJSON Structure
- **LineString Features:** Each route profile (`balanced`, `direct`, `safe`) has a `LineString` feature with coordinates `[lon, lat, elevation]`.
- **Properties on LineString:**
  - `profile`: "balanced" | "direct" | "safe"
  - `total_distance_m`: number
  - `estimated_risk_score`: number (0-100)
  - `max_slope_deg`: number
  - `traverse_time_hr`: number
- **Point Features:** Waypoints for start, destination, and key path points:
  - `type`: "start" | "goal" | "waypoint"
  - `step_index`: integer
  - `elevation_m`: number
  - `slope_deg`: number
  - `risk_score`: number
  - `cumulative_distance_m`: number

---

## 4. Coordinate Semantics

| Coordinate System | Units | Origin / Orientation | Usage |
|:---|:---|:---|:---|
| **Grid Coordinates (`GridCoordinate`)** | Integer cells (`x`, `y`) | `(0, 0)` is Top-Left (North-West); `x` increases Eastward, `y` increases Southward | Internal raster matrix indexing, cost arrays, A\* search |
| **Mars Geographic (`MarsCoordinate`)** | Decimal Degrees (`lon`, `lat`) | IAU 2000 Mars sphere; Jezero center ~`77.45°E`, `18.38°N` | Frontend display, GeoJSON layers, NASA WMTS alignment |

Conversion between coordinates is handled by `JezeroCoordinateTransformer`:
```python
from algorithms.grid import JezeroCoordinateTransformer, create_jezero_default_grid_spec

spec = create_jezero_default_grid_spec(width=100, height=100, resolution_m=10.0)
transformer = JezeroCoordinateTransformer(spec)

# Forward transform (lon/lat -> grid)
grid_x, grid_y = transformer.mars_to_grid(lon=77.45, lat=18.38)

# Inverse transform (grid -> lon/lat)
lon, lat = transformer.grid_to_mars(grid_x=50, grid_y=50)
```

---

## 5. NASA Data Truthfulness & Safety Caveats

1. **Synthetic vs. Real Data:**  
   The benchmark dataset in `sample_jezero_grid.py` is labeled `SYNTHETIC_BENCHMARK_DEM`. It is modeled after published Jezero topography for testing and UI integration. Real NASA HiRISE and MOLA GeoTIFF rasters must be integrated by Developer B via GDAL/Rasterio when available.
2. **Safety Disclaimer:**  
   All risk scores are **project-generated algorithmic estimates**, NOT official NASA flight certifiable measurements. Never describe any generated route as "guaranteed safe".
3. **Resolution Limits:**  
   Orbital imagery and DEMs cannot resolve sub-meter hazards (e.g. 30cm sharp rocks, localized dust ponds, or micro-dune sand traps). Rover-scale autonomous obstacle detection (AutoNav) remains essential for real-world rover safety.

---

## 6. How to Run Tests and Demo

Run all unit and integration tests (29 tests):
```powershell
python -m unittest discover -s algorithms/tests -v
```

Run the end-to-end interactive mission simulation demo:
```powershell
python -m algorithms.demo
```
This runs two mission scenarios (Delta ramp descent and Séítah hazard avoidance) and exports `sample_mission_route.geojson`.
