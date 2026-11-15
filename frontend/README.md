# MARSWALK — Frontend Application

Intelligent Mars Exploration & Mission Planning System (Jezero Crater)

**Role:** Developer A — Frontend Engineer  
**Branch:** `feature/frontend`  
**Stack:** React 18, TypeScript, Vite, OpenLayers (`ol`), Tailwind CSS, Lucide Icons

---

## 1. Quick Start

### Prerequisites
- Node.js >= 18.x
- npm >= 9.x

### Installation & Run
```bash
cd frontend
npm install
npm run dev
```
The frontend dev server runs on `http://localhost:5173`.

### Production Build & Verification
```bash
npm run build
npm run preview
```

---

## 2. Architecture & Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Header.tsx                     # Mission control telemetry header, Sol clock, backend status
│   │   ├── MarsMap.tsx                    # OpenLayers interactive Jezero Crater map (EPSG:4326)
│   │   ├── ElevationProfileChart.tsx      # SVG elevation & slope chart across route waypoints
│   │   ├── MissionReportModal.tsx         # Printable & JSON-exportable mission brief
│   │   └── Sidebar/
│   │       ├── RoutePlannerPanel.tsx      # A* route planning, constraints, alternatives comparison
│   │       ├── LayerControlPanel.tsx      # Base and overlay layer toggles, opacity sliders
│   │       ├── HazardTelemetryPanel.tsx   # Jezero hazards, risk ratings, mitigation protocols
│   │       └── ScienceObservationsPanel.tsx # NASA Perseverance PDS science targets
│   ├── services/
│   │   ├── apiClient.ts                   # API client connecting to Developer B's FastAPI with mock fallback
│   │   └── mapManager.ts                  # OpenLayers layers, projections, hazards, route geometry
│   ├── types/
│   │   └── api.ts                         # Shared TypeScript interfaces for API contract
│   ├── App.tsx                            # Root mission control dashboard coordinator
│   ├── index.css                          # Custom aerospace mission-control styling & animations
│   └── main.tsx                           # Application mount point
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts                         # Configured with /api proxy to http://localhost:8000
```

---

## 3. NASA Data Provenance & Verification

1. **NASA Mars Trek WMTS (Viking MDIM2.1 Global Color Mosaic, 232m/pixel)**:
   - Endpoint: `https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0//default/default028mm/{z}/{y}/{x}.jpg`
   - Verified via WMTS GetCapabilities with CORS support (`Access-Control-Allow-Origin: *`).
2. **NASA Mars Global Surveyor MOLA Shaded Relief (463m/pixel)**:
   - Endpoint: `https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg`
3. **NASA Mars 2020 Perseverance PDS Science Targets**:
   - Octavia E. Butler Landing (Sol 0)
   - Séítah South Olivine Ripple Field (Sol 198)
   - Kodiak Butte Delta Remnant (Sol 380)
   - Enchanted Lake Delta Base (Sol 435)
   - Skinner Ridge Delta Scarp (Sol 510)
   - Three Forks Sample Depot (Sol 654)
   - Belva Crater South Rim (Sol 755)
4. **Historical Perseverance Traverse Track**:
   - Vector line rendered directly on the map tracing the rover's actual historical path across the Jezero western delta.

---

## 4. Route Profile Alignment (Developer C)

Route optimization profiles strictly adhere to Developer C's `algorithms/models.py` and `algorithms/routing/alternatives.py`:

| UI Label | Backend Profile Identifier | Description | Standoff / Slope Constraints |
| :--- | :--- | :--- | :--- |
| **Fastest** | `direct` | Minimum Euclidean distance traverse | Standard 20° slope threshold, small 6m buffer |
| **Balanced** | `balanced` | Nominal mission compromise (distance vs safety) | 20° slope limit, 15m hazard buffer, moderate roughness weight |
| **Safest** | `safe` | Maximum hazard buffer & gentle slopes | Strict 18° limit, heavy slope penalty, 25m hazard buffer |
| **Science Max** | *Disabled* | Visited sediment & mineral outcrop targets | **Disabled in UI** until validated backend/algorithm implementation exists |

*Engineering Rule:* The frontend does **not** silently alias or map `Science Max` to another profile. It is presented in a disabled state with explicit status labeling.

---

## 5. Mars Coordinate and Projection Audit

- **Coordinate Conventions:**
  - Standard planetographic / IAU 2000 Mars sphere ($R_{Mars} = 3,389,500$ meters).
  - **Longitude:** Degrees East (positive East in range `[77.0, 77.8]°E`).
  - **Latitude:** Degrees North (positive North in range `[18.2, 18.7]°N`).
- **GeoJSON Specifications:**
  - Coordinate order is strictly `[longitude, latitude]` (or `[longitude, latitude, elevation_m]`).
- **Raster Row/Column Orientation:**
  - Row 0: Northern boundary (`18.7°N`).
  - Row 64: Southern boundary (`18.2°N`).
  - Column 0: Western boundary (`77.0°E`).
  - Column 102: Eastern boundary (`77.8°E`).
  - Formula: $\text{col} = \text{round}\left(\frac{\text{lon} - 77.0}{77.8 - 77.0} \times (W - 1)\right)$, $\text{row} = \text{round}\left(\frac{18.7 - \text{lat}}{18.7 - 18.2} \times (H - 1)\right)$.
- **OpenLayers View Projection:**
  - Configured with `projection: 'EPSG:4326'` (Equirectangular / Plate Carrée).
  - OpenLayers ScaleLine control displays degree-based metric approximations; all mission-critical distance calculations on frontend use the Mars-specific Haversine formulation with $R = 3,389,500$ m.

---

## 6. Route Response Parsing & Live API vs Demo Mode

### Dual Schema Parsing
The frontend API client handles:
1. **Developer B's FastAPI `RoutePlanResponse` Schema:**
   - Parsed from `routes: [ { id, label, path: [{ longitude, latitude, row, column }], distance_meters, maximum_slope_degrees, mean_slope_degrees, risk_level, ... } ]`.
   - Primary route (`routes[0]`) and alternatives (`routes[1..n]`).
   - Graceful handling of unreachable or blocked paths without fabricating results.
2. **Developer C's GeoJSON `FeatureCollection` Format:**
   - Parsed from `type: "FeatureCollection"`, extracting LineString geometry and Point waypoints.

### Transparent Operation Modes
- **Backend Online:** Displays `LIVE BACKEND CALCULATION (A* Engine)` and green `API: LIVE` badge.
- **Backend Offline:** Displays `DEMO SIMULATION (Backend Offline)` in amber with prominent notice that calculations use local synthetic/prototype test data and are not live NASA-derived calculations.

---

## 7. Transparent Safety Notice & Known Limitations

- **Mission Planning Prototype Only:** MARSWALK is designed for research and mission planning. Trajectories are not certified for flight operations.
- **Orbital Sensor Limits:** Satellite and orbital imagery cannot resolve sub-meter rocks, loose regolith softness, or micro-dune slips.
- **Risk Score Semantics:** All risk scores and hazard outlines are project-generated models produced from MOLA/HiRISE datasets, not official NASA mission navigation measurements. Never describe a generated route as guaranteed safe.
