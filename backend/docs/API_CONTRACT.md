# MARSWALK API Contract & Integration Specification

**Version:** 0.1.0  
**Owner:** Developer B (Backend and NASA Data Engineer)  
**Target Region:** Jezero Crater, Mars (Lon 77.0°–77.8°E, Lat 18.2°–18.7°N)  
**CRS:** EPSG:4326 (Mars Geographic Longitude / Latitude in Degrees)  
**Disclaimer:** *MARSWALK is a research and mission-planning prototype. It is NOT an operational rover-navigation or safety-certified system.*

---

## 1. Architectural Overview & Coordinate Semantics

### Explicit Coordinate Rules
To avoid bugs when integrating between Developer A (Frontend / OpenLayers), Developer B (FastAPI Backend), and Developer C (Pathfinding Algorithms):

1. **Mars Geographic Coordinates (`lon`, `lat`):**
   - Floating-point degrees in Mars standard planetographic / IAU2000 coordinates (EPSG:4326 equivalent).
   - Longitude: Positive East in range `[77.0, 77.8]`.
   - Latitude: Positive North in range `[18.2, 18.7]`.
   - Used in: User input, map markers, map layer bounding boxes, GeoJSON paths.

2. **Route Grid Coordinates (`row`, `col`):**
   - Zero-indexed integer grid indices: `0 <= row < 65` and `0 <= col < 103`.
   - **Row 0:** Northernmost latitude (`18.7°N`).
   - **Row 64:** Southernmost latitude (`18.2°N`).
   - **Column 0:** Westernmost longitude (`77.0°E`).
   - **Column 102:** Easternmost longitude (`77.8°E`).
   - Cell resolution: 128 pixels/degree ($\approx 463.0$ meters per pixel at equator).
   - Used in: Raster array slicing, graph adjacency, internal A* path search.

3. **Coordinate Transformation Formulas:**
   ```python
   # Geographic to Grid
   col = int(round((longitude - 77.0) / (77.8 - 77.0) * (width - 1)))
   row = int(round((18.7 - latitude) / (18.7 - 18.2) * (height - 1)))

   # Grid to Geographic
   longitude = 77.0 + (col / (width - 1)) * (77.8 - 77.0)
   latitude = 18.7 - (row / (height - 1)) * (18.7 - 18.2)
   ```

---

## 2. Standard Error Envelope

All error responses across all HTTP status codes (400, 404, 422, 500, 502) adhere strictly to this schema:

```json
{
  "error": {
    "code": "INVALID_REQUEST | NOT_FOUND | UPSTREAM_UNAVAILABLE | DATA_UNAVAILABLE | INTERNAL_ERROR",
    "message": "Human-readable explanation of error.",
    "details": {}
  }
}
```

*Note: Stack traces are never exposed in API responses.*

---

## 3. Endpoints

### 3.1 Health Check
**`GET /api/health`**

Monitors the backend service and probes upstream NASA services without failing if NASA is temporarily offline.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "service": "marswalk-backend",
  "version": "0.1.0",
  "time_utc": "2026-11-14T09:20:00Z",
  "dependencies": {
    "nasa_trek": "available",
    "nasa_pds": "available",
    "route_engine": "available"
  }
}
```

---

### 3.2 Exploration Regions
**`GET /api/regions`**

Returns primary exploration sectors, spatial boundaries, and data coverage status.

**Response `200 OK`:**
```json
{
  "regions": [
    {
      "id": "jezero_crater",
      "name": "Jezero Crater",
      "description": "Primary MARSWALK exploration region",
      "bbox": {
        "min_lon": 77.0,
        "min_lat": 18.2,
        "max_lon": 77.8,
        "max_lat": 18.7
      },
      "crs": "EPSG:4326",
      "data_coverage": {
        "imagery": "available",
        "topography": "available",
        "observations": "available"
      },
      "sources": [
        "NASA Mars Trek (WMTS)",
        "NASA Mars Global Surveyor (MGS) MOLA MEGDR",
        "NASA Mars 2020 Perseverance Mission Context"
      ]
    }
  ]
}
```

---

### 3.3 Map Layers (WMTS Metadata)
**`GET /api/layers?region_id=jezero_crater`**

Provides verified OGC WMTS layer templates for OpenLayers. Every layer identifier, tile matrix set, and resource URL template is validated against live NASA Mars Trek `WMTSCapabilities.xml`. Unverified layers are returned with `status: "unavailable"` and `url: null`.

**Response `200 OK`:**
```json
{
  "region_id": "jezero_crater",
  "layers": [
    {
      "id": "nasa_mars_trek_ctx",
      "name": "NASA Mars Trek CTX Mosaic (Caltech Beta)",
      "type": "wmts",
      "status": "available",
      "url": "https://astro.arcgis.com/arcgis/rest/services/OnMars/CTX/MapServer/tile/{TileMatrix}/{TileRow}/{TileCol}",
      "attribution": "NASA/JPL-Caltech/MSSS/Murray Lab",
      "source_url": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars",
      "coverage": {
        "min_lon": -180.0,
        "min_lat": -65.0,
        "max_lon": 180.0,
        "max_lat": 65.0
      },
      "limitations": [
        "Global uncontrolled CTX mosaic at ~5-6m resolution.",
        "May contain seamlines, lighting variations, or small spatial registration offsets.",
        "Visual imagery alone does not guarantee obstacle detectability."
      ]
    },
    {
      "id": "nasa_mars_trek_mola_shade",
      "name": "NASA Mars Trek MOLA Color Hillshade",
      "type": "wmts",
      "status": "available",
      "url": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{TileMatrix}/{TileRow}/{TileCol}.jpg",
      "attribution": "NASA/JPL-Caltech/GSFC",
      "source_url": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars",
      "coverage": {
        "min_lon": -180.0,
        "min_lat": -90.0,
        "max_lon": 180.0,
        "max_lat": 90.0
      },
      "limitations": [
        "Coarse (~463 m/pixel) global topographic shaded relief.",
        "Stylized color palette representing regional elevation variations."
      ]
    },
    {
      "id": "nasa_mars_trek_hirise_jezero_unverified",
      "name": "NASA Mars Trek HiRISE Jezero DEM Mosaic (Unverified Candidate)",
      "type": "wmts",
      "status": "unavailable",
      "url": null,
      "attribution": "NASA/JPL-Caltech/Univ. of Arizona",
      "source_url": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars",
      "coverage": {
        "min_lon": 77.0,
        "min_lat": 18.0,
        "max_lon": 78.5,
        "max_lat": 19.5
      },
      "limitations": [
        "WMTS endpoint returned 404 during automated capability verification.",
        "Layer marked as unavailable in compliance with NASA data verification rules."
      ]
    }
  ]
}
```

---

### 3.4 Scientific Observations & Rover Targets
**`GET /api/observations?region_id=jezero_crater&limit=50&source=demo`**

Retrieves science targets, rover waypoints, and imagery markers. Real NASA PDS items are distinguished from clearly labeled demonstration datasets.

**Response `200 OK`:**
```json
{
  "region_id": "jezero_crater",
  "count": 4,
  "observations": [
    {
      "id": "demo_perseverance_octavia_butler",
      "title": "Octavia E. Butler Landing Site (Sol 0)",
      "type": "science_target",
      "longitude": 77.4509,
      "latitude": 18.4447,
      "sol": 0,
      "acquired_at": "2021-02-18T20:55:00Z",
      "source": "MARSWALK demo dataset",
      "source_url": "https://mars.nasa.gov/mars2020/",
      "dataset_id": "MARSWALK-JEZERO-DEMO-2026",
      "description": "Touchdown location of the Mars 2020 Perseverance Rover in Jezero Crater.",
      "thumbnail_url": "https://mars.nasa.gov/system/resources/detail_files/25679_PIA24424-web.jpg",
      "provenance": {
        "retrieved_at": "2026-11-14T09:20:00Z",
        "verification_status": "simulated",
        "limitations": [
          "Demonstration data; not a NASA observation.",
          "Synthesized science waypoint markers for mission-planning UI demonstration."
        ]
      }
    }
  ]
}
```

---

### 3.5 Topographic Terrain Grid
**`GET /api/terrain?region_id=jezero_crater&resolution=coarse`**

Delivers verified elevation and central-difference slope matrices. Backed by authentic NASA MGS MOLA MEGDR data (`MEGT00N000HB.IMG`).

**Response `200 OK`:**
```json
{
  "region_id": "jezero_crater",
  "status": "available",
  "grid": {
    "width": 103,
    "height": 65,
    "cell_size_meters": 463.0,
    "origin_lon": 77.0,
    "origin_lat": 18.2,
    "crs": "EPSG:4326"
  },
  "elevation": {
    "available": true,
    "unit": "meters",
    "source": "NASA MOLA",
    "source_url": "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt00n000hb.lbl",
    "resolution_meters": 463.0,
    "values": [
      [179.0, 185.0, "..."],
      ["..."]
    ]
  },
  "slope": {
    "available": true,
    "unit": "degrees",
    "method": "central difference on elevation grid",
    "values": [
      [2.3, 3.1, "..."],
      ["..."]
    ]
  },
  "roughness": {
    "available": false,
    "unit": "unitless",
    "method": "not available in MVP",
    "values": []
  },
  "provenance": {
    "retrieved_at": "2026-11-14T09:20:00Z",
    "limitations": [
      "Derived from NASA Mars Global Surveyor (MGS) MOLA MEGDR topography (128 pixels/degree, ~463 m/pixel).",
      "MOLA-derived elevation is coarse relative to rover-scale navigation (~2 m wheelbase). Micro-topographic features and boulders are not captured.",
      "Slope values are calculated via central difference gradient methods on the coarse elevation grid.",
      "MARSWALK is a research and mission-planning prototype. It is NOT an operational rover-navigation or safety-certified system."
    ]
  }
}
```

---

### 3.6 Hazards Evaluation
**`GET /api/hazards?region_id=jezero_crater`**

Provides a 0-100 composite hazard grid derived from terrain slope gradients.

**Response `200 OK`:**
```json
{
  "region_id": "jezero_crater",
  "status": "available",
  "hazard_score": {
    "available": true,
    "unit": "0-100",
    "method": "project-generated heuristic",
    "values": [
      [12.8, 15.5, "..."],
      ["..."]
    ]
  },
  "hazard_types": [
    {
      "id": "steep_slope",
      "name": "Steep slope",
      "basis": "Derived from MOLA elevation gradient",
      "confidence": "medium",
      "available": true
    }
  ],
  "provenance": {
    "retrieved_at": "2026-11-14T09:20:00Z",
    "limitations": [
      "Hazard scores are MARSWALK estimates, not official NASA safety assessments.",
      "Imagery-based hazards (such as boulder fields, sand ripples, and loose sand traps) are not comprehensively detected in the MVP.",
      "Terrain slope is evaluated from orbital MOLA altimetry at coarse (~463 m) resolution."
    ]
  }
}
```

---

### 3.7 Route Planning
**`POST /api/routes/plan`**

Plans optimal and alternative rover traverse paths using A* graph search across the terrain grid.

**Request:**
```json
{
  "region_id": "jezero_crater",
  "start": {
    "longitude": 77.35,
    "latitude": 18.45
  },
  "goal": {
    "longitude": 77.55,
    "latitude": 18.55
  },
  "options": {
    "max_slope_degrees": 25.0,
    "avoid_hazards": true,
    "hazard_weight": 0.4,
    "slope_weight": 0.3,
    "distance_weight": 0.3,
    "alternatives": 2
  }
}
```

**Response `200 OK`:**
```json
{
  "request_id": "route_req_abc123",
  "region_id": "jezero_crater",
  "status": "success",
  "routes": [
    {
      "id": "route_7f8a9b",
      "label": "Primary route",
      "algorithm": "A*",
      "start": { "longitude": 77.35, "latitude": 18.45 },
      "goal": { "longitude": 77.55, "latitude": 18.55 },
      "path": [
        { "longitude": 77.35, "latitude": 18.45, "row": 32, "column": 45 },
        { "longitude": 77.3578, "latitude": 18.4578, "row": 31, "column": 46 }
      ],
      "distance_meters": 13420.5,
      "estimated_travel_time_minutes": 4970.6,
      "mean_slope_degrees": 5.42,
      "maximum_slope_degrees": 12.18,
      "mean_hazard_score": 23.4,
      "maximum_hazard_score": 46.4,
      "risk_level": "medium",
      "data_coverage": {
        "elevation": "available",
        "hazards": "available"
      },
      "warnings": [],
      "provenance": {
        "generated_at": "2026-11-14T09:20:00Z",
        "cost_model": "distance + slope + hazard proximity (Backend A* fallback implementation)",
        "limitations": [
          "MARSWALK is a research and mission-planning prototype, not an operational or safety-certified navigation system.",
          "Orbital imagery and coarse topography cannot detect small-scale obstacles, rocks, or loose regolith.",
          "Planned routes are computational estimations and are not guaranteed safe."
        ]
      }
    }
  ],
  "message": "Route is a planning estimate and is not guaranteed safe."
}
```

**Error `422 Unprocessable Entity` (Out of Bounds):**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Start coordinate (10.0, 18.45) is outside the Jezero Crater region [77.0, 18.2, 77.8, 18.7].",
    "details": {}
  }
}
```

---

### 3.8 Mission Creation & Retrieval

#### Create Mission
**`POST /api/missions`**

**Request:**
```json
{
  "region_id": "jezero_crater",
  "name": "Jezero Delta Front Traverse",
  "route_id": "route_7f8a9b",
  "notes": "Traverse investigating lacustrine delta clay minerals and depositing sample cache."
}
```

**Response `201 Created`:**
```json
{
  "id": "mission_92fa34b01e",
  "name": "Jezero Delta Front Traverse",
  "region_id": "jezero_crater",
  "route_id": "route_7f8a9b",
  "created_at": "2026-11-14T09:20:00Z",
  "status": "draft",
  "summary": {
    "distance_meters": 1420.5,
    "risk_level": "medium",
    "mean_slope_degrees": 6.8,
    "maximum_slope_degrees": 14.2,
    "hazard_score": 28.4,
    "observations": 4
  },
  "report": {
    "title": "MARSWALK Mission Plan",
    "sections": [
      {
        "title": "Route overview",
        "content": "Mission 'Jezero Delta Front Traverse' planned in primary exploration sector jezero_crater..."
      },
      {
        "title": "Terrain and hazards",
        "content": "Traverse encounters an average gradient of 6.8° with peak slopes of 14.2°..."
      },
      {
        "title": "Scientific context",
        "content": "The planned route intersects 4 high-priority scientific targets within Jezero Crater..."
      },
      {
        "title": "Limitations",
        "content": "MARSWALK is a mission-planning and research prototype. It is NOT an operational rover-navigation or safety-certified system..."
      }
    ]
  },
  "notes": "Traverse investigating lacustrine delta clay minerals and depositing sample cache."
}
```

#### Get Mission
**`GET /api/missions/{id}`**

Returns the saved mission or `404 Not Found` if the mission ID does not exist.

---

## 4. Developer A (Frontend) Integration Notes
1. **OpenLayers Basemap Integration:**
   - Use `GET /api/layers` to dynamically populate map basemaps.
   - For `nasa_mars_trek_ctx`, bind OpenLayers `XYZ` or `WMTS` source directly to the returned `url`.
2. **Route Display:**
   - The `routes[].path` list contains both geographic `{"longitude", "latitude"}` (for direct OpenLayers LineString geometry) and grid indices `{"row", "column"}`.
3. **Disclaimers & Limitations:**
   - Always display `message` and `provenance.limitations` on the route planning UI card to ensure transparency regarding non-operational research status.

---

## 5. Developer C (Algorithms) Integration Notes
1. **Engine Integration Status:**
   - Developer C's `AlternativeRoutePlanner` (`algorithms.routing.alternatives`) is **fully integrated** into `route_service.py`.
   - The route planner uses the actual NASA MOLA MEGDR DEM grid (`65 × 103` at `463.0 m` resolution) and slope/hazard buffers, NOT synthetic benchmark data.
   - All three routing profiles are supported: `balanced` (default), `direct` (shortest distance), and `safe` (maximum hazard standoff).
2. **Stable Grid Metadata:**
   - Height: 65 rows, Width: 103 columns.
   - Cell Size: 463.0 meters.
   - Row 0 corresponds to latitude 18.7°N; Row 64 corresponds to latitude 18.2°N.
   - Column 0 corresponds to longitude 77.0°E; Column 102 corresponds to longitude 77.8°E.
3. **GeoJSON & Multi-Route Outputs:**
   - Responses include full OpenLayers-ready `geojson` FeatureCollection containing both route LineStrings and key turn/waypoint Points.
   - Comparative profile trade-offs are included in `comparison`.
