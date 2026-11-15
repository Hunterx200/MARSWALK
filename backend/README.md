# MARSWALK — Backend Service

Intelligent Mars Exploration & Mission Planning API built with **FastAPI**, **Pydantic v2**, and **NumPy**.

## Overview
The MARSWALK backend provides exploration metadata, verified NASA Mars Trek WMTS tile layer endpoints, authentic MOLA topographic elevation data, slope-derived hazard matrices, A* traverse route planning, and automated mission report generation for **Jezero Crater, Mars**.

> **Disclaimer:** MARSWALK is a research and mission-planning prototype. It is NOT an operational rover-navigation or safety-certified system.

---

## Directory Structure
```
backend/
├── app/
│   ├── main.py                     # FastAPI application and CORS setup
│   ├── config.py                   # Environment and bounding box settings
│   ├── api/
│   │   ├── routes_health.py        # /api/health
│   │   ├── routes_regions.py       # /api/regions
│   │   ├── routes_layers.py        # /api/layers
│   │   ├── routes_observations.py  # /api/observations
│   │   ├── routes_terrain.py       # /api/terrain
│   │   ├── routes_hazards.py       # /api/hazards
│   │   ├── routes_routes.py        # /api/routes/plan
│   │   └── routes_missions.py      # /api/missions
│   ├── schemas/
│   │   ├── common.py               # Shared error and coordinate schemas
│   │   ├── region.py               # Exploration regions
│   │   ├── layer.py                # WMTS map layer schemas
│   │   ├── observation.py          # Science waypoints & observations
│   │   ├── terrain.py              # Grid, elevation & slope matrices
│   │   ├── hazard.py               # Heuristic hazard scores
│   │   ├── route.py                # Path, options, and route plan schemas
│   │   └── mission.py              # Mission report and summary schemas
│   ├── services/
│   │   ├── nasa_trek.py            # Mars Trek WMTS GetCapabilities parser
│   │   ├── nasa_pds.py             # PDS observation search & demo targets
│   │   ├── terrain_service.py      # MGS MOLA MEGDR elevation & slope grid
│   │   ├── hazard_service.py       # Slope-derived hazard evaluation
│   │   ├── route_service.py        # A* graph pathfinding engine (fallback)
│   │   └── mission_service.py      # In-memory mission store & synthesis
│   ├── core/
│   │   ├── errors.py               # Custom exceptions & global handlers
│   │   └── provenance.py           # UTC timestamps & disclaimers
│   └── data/
│       └── jezero_mola_128ppd.npy  # Verified NASA MOLA 128ppd MEGDR slice
├── docs/
│   └── API_CONTRACT.md             # Shared API contract specification
├── tests/
│   ├── test_health.py              # Health check tests
│   ├── test_api_contract.py        # Contract & schema compliance tests
│   ├── test_route_planning.py      # Pathfinding & coordinate bounds tests
│   └── test_nasa_metadata.py       # NASA WMTS & terrain data integrity tests
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 2. Run Tests
```bash
pytest
```

### 3. Start the Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```
API Documentation is available interactively at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Verified NASA Data Sources

| Source Name | Endpoint / Dataset | Verified Capabilities | Status | Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **NASA Mars Trek (MRO CTX)** | `CTX_beta01_uncontrolled_5m_Caltech` | RESTful WMTS ResourceURL parsed from `WMTSCapabilities.xml` | **Available** | Global uncontrolled mosaic at 5-6 m resolution. Seamlines and minor registration offsets may occur. |
| **NASA Mars Trek (MGS MOLA)** | `Mars_MGS_MOLA_ClrShade_merge_global_463m` | RESTful WMTS GetCapabilities XML verified; live tiles tested | **Available** | Global color hillshade at coarse ~463 m/pixel resolution. Stylized color representation. |
| **NASA Mars Trek (Viking MDIM2.1)** | `Mars_Viking_MDIM21_ClrMosaic_global_232m` | RESTful WMTS GetCapabilities XML verified | **Available** | Global mosaic at 232 m/pixel resolution. Sensor resolution limits rover-scale tactical detail. |
| **NASA MGS MOLA MEGDR** | `MEGT00N000HB.IMG` (PDS Geosciences) | Fixed-record binary topography sliced via HTTP Range request | **Available** | 128 pixels/degree (~463 m/pixel). Coarse relative to rover wheelbase (~2m). Micro-topography not captured. |
| **NASA PDS Imaging Atlas** | `https://pds-imaging.jpl.nasa.gov/api/search/atlas/_search` | ElasticSearch search API verified | **Available / Partial** | Live queries supported; local demo dataset provided for reliable, fast hackathon workflow. |

---

## Integration Guide

### Developer A (Frontend)
- **Base URL:** `http://localhost:8000`
- **Basemaps:** Call `GET /api/layers` to get live WMTS tile URLs for OpenLayers.
- **Route Coordinates:** `POST /api/routes/plan` returns paths with both Mars geographic coordinates (`longitude`, `latitude`) for map rendering and grid indices (`row`, `column`).
- **Observations:** Call `GET /api/observations` to render science waypoints and Perseverance landing/depot markers on the map.

### Developer C (Algorithms)
- **Grid Dimensions:** 65 rows × 103 columns covering Jezero Crater `[77.0, 18.2, 77.8, 18.7]`.
- **Topography:** Backed by authentic MGS MOLA MEGDR elevation data (`463.0 m` resolution).
- **Hazards:** Real elevation gradients drive the hazard mask and standoff proximity grid.
- **Engine Integration:** Fully integrated with Developer C's `AlternativeRoutePlanner` across `direct`, `balanced`, and `safe` profiles, emitting GeoJSON features and comparison metrics.
