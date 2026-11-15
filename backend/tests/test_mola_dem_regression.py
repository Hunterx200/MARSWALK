"""Regression test suite verifying official NASA MGS MOLA MEGDR 128ppd DEM remediation."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.terrain_service import terrain_service
from app.services.route_service import route_service
from app.schemas.common import GeoCoordinate
from app.schemas.route import RoutePlanRequest
from algorithms.routing.alternatives import AlternativeRoutePlanner


def test_mola_dem_provenance_and_elevation_samples():
    """Verify official MEGT44N000HB DEM provenance, array SHA-256, shape, and landing-site elevation."""
    dem_path = Path("backend/app/data/jezero_mola_128ppd.npy")
    prov_path = Path("backend/app/data/jezero_mola_provenance.json")

    assert dem_path.exists(), "DEM array file must exist"
    assert prov_path.exists(), "DEM provenance metadata must exist"

    with open(prov_path, "r") as f:
        meta = json.load(f)

    assert meta["product_id"] == "MEGT44N000HB.IMG"
    assert meta["source_dataset_id"] == "MGS-M-MOLA-5-MEGDR-L3-V1.0"
    assert meta["http_status"] == 206
    assert meta["content_range"] == "bytes 74603520-76101119/129761280"

    with open(dem_path, "rb") as f:
        file_sha = hashlib.sha256(f.read()).hexdigest()

    assert file_sha == meta["file_sha256"]
    assert file_sha == "aa48c8f76fbc0cb151f947b868640f29cce039d9b6ba7a208e4e8773379747e3"

    arr = np.load(dem_path)
    assert arr.shape == (65, 103)
    assert arr.dtype == np.int16

    # Jezero Northern Hemisphere topography: elevations range from -2719m to -1537m
    assert arr.min() == -2719
    assert arr.max() == -1537
    assert -2350 < arr.mean() < -2300

    # Perseverance Octavia E. Butler Landing site (~18.4447°N, 77.4509°E) maps to [33, 57]
    site_elevation = int(arr[33, 57])
    assert site_elevation == -2571
    assert -2580 <= site_elevation <= -2560


@pytest.mark.asyncio
async def test_all_four_mission_boundary_corners():
    """Verify route planning succeeds across all four mission exploration boundary corners."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        center = {"longitude": 77.45, "latitude": 18.45}
        corners = [
            ("SW Corner", {"longitude": 77.0, "latitude": 18.2}),
            ("SE Corner", {"longitude": 77.8, "latitude": 18.2}),
            ("NW Corner", {"longitude": 77.0, "latitude": 18.7}),
            ("NE Corner", {"longitude": 77.8, "latitude": 18.7}),
        ]

        for name, corner in corners:
            # Route from corner to center
            req_in = {
                "region_id": "jezero_crater",
                "start": corner,
                "goal": center,
                "options": {"profile": "balanced", "alternatives": 2}
            }
            resp_in = await ac.post("/api/routes/plan", json=req_in)
            assert resp_in.status_code == 200, f"{name} inward route failed: {resp_in.text}"
            data_in = resp_in.json()
            assert data_in["status"] == "success", f"{name} route status must be success"
            assert len(data_in["routes"]) >= 1

            # Route from center to corner
            req_out = {
                "region_id": "jezero_crater",
                "start": center,
                "goal": corner,
                "options": {"profile": "balanced", "alternatives": 2}
            }
            resp_out = await ac.post("/api/routes/plan", json=req_out)
            assert resp_out.status_code == 200, f"{name} outward route failed: {resp_out.text}"
            data_out = resp_out.json()
            assert data_out["status"] == "success"


def test_boundary_snapping_distance_and_rejection():
    """Verify edge snapping distance calculation, endpoint preservation, and out-of-boundary rejection."""
    # Test valid boundary corner snapping
    row, col, snapped, dist_m = route_service.snap_endpoint(
        GeoCoordinate(longitude=77.8, latitude=18.2), "TestSECorner"
    )
    assert col == 101
    assert row == 63
    assert 500.0 < dist_m < 600.0  # Approx 574.5m
    assert snapped.longitude == 77.792969
    assert snapped.latitude == 18.207031

    # Test out-of-region coordinates rejected
    with pytest.raises(Exception):
        route_service.validate_coordinates(GeoCoordinate(longitude=78.5, latitude=18.5), "OutEast")

    with pytest.raises(Exception):
        route_service.validate_coordinates(GeoCoordinate(longitude=77.4, latitude=19.2), "OutNorth")


def test_bilinear_interpolation_interior_and_edges():
    """Verify 4-point bilinear interpolation inside DEM and discrete fallback on margins with zero IndexError."""
    # Interior cell center (u=32.0, v=20.0)
    lon_center = 77.00390625 + 32 / 128.0
    lat_center = 18.69921875 - 20 / 128.0
    elev_center = terrain_service.get_elevation_at(lon_center, lat_center)
    expected_center = float(terrain_service._elevation[20, 32])
    assert abs(elev_center - expected_center) < 1e-3

    # Exact boundary edge: Easternmost cell center u=102.0, Southernmost v=64.0
    lon_edge = 77.00390625 + 102 / 128.0
    lat_edge = 18.69921875 - 64 / 128.0
    elev_edge = terrain_service.get_elevation_at(lon_edge, lat_edge)
    assert abs(elev_edge - float(terrain_service._elevation[64, 102])) < 1e-3

    # Margin point: u=102.3, v=64.2 (outer boundary margin)
    lon_margin = 77.00390625 + 102.3 / 128.0
    lat_margin = 18.69921875 - 64.2 / 128.0
    elev_margin = terrain_service.get_elevation_at(lon_margin, lat_margin)
    assert elev_margin == float(terrain_service._elevation[64, 102])

    # Out of footprint point: u=103.0 -> ValueError
    lon_outside = 77.00390625 + 103.0 / 128.0
    lat_outside = 18.45
    with pytest.raises(ValueError):
        terrain_service.get_elevation_at(lon_outside, lat_outside)


def test_slope_calculation_anisotropy_and_orientations():
    """Verify slope gradient computation handles anisotropic grid spacing correctly."""
    dy = 463.09
    dx = 439.29

    # 1. Flat plane -> 0 slope
    flat = np.full((10, 10), -2500.0, dtype=float)
    gy, gx = np.gradient(flat, dy, dx)
    slope_flat = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
    assert np.allclose(slope_flat, 0.0)

    # 2. Pure North-South 1:1 incline (rise = dy) -> 45 degrees
    ns_grid = np.zeros((10, 10), dtype=float)
    for r in range(10):
        ns_grid[r, :] = r * dy
    gy, gx = np.gradient(ns_grid, dy, dx)
    slope_ns = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
    assert np.allclose(slope_ns[1:-1, 1:-1], 45.0, atol=1e-3)

    # 3. Pure East-West 1:1 incline (rise = dx) -> 45 degrees
    ew_grid = np.zeros((10, 10), dtype=float)
    for c in range(10):
        ew_grid[:, c] = c * dx
    gy, gx = np.gradient(ew_grid, dy, dx)
    slope_ew = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
    assert np.allclose(slope_ew[1:-1, 1:-1], 45.0, atol=1e-3)


def test_hard_hazard_exclusion_all_profiles():
    """Verify that direct, balanced, and safe profiles strictly avoid hazard-masked cells."""
    dem = terrain_service._elevation.copy()
    hazard_mask = np.zeros_like(dem, dtype=bool)
    # Create impassable vertical barrier in column 50
    hazard_mask[10:50, 50] = True

    planner = AlternativeRoutePlanner(
        dem=dem,
        hazard_mask=hazard_mask,
        resolution_m=463.0,
    )

    res = planner.plan_multi_routes(start=(30, 25), goal=(70, 25))
    assert res.primary.found

    for r in [res.primary] + res.alternatives:
        for wp in r.waypoints:
            assert not hazard_mask[wp.grid_y, wp.grid_x], f"Profile {r.profile} traversed masked hazard at ({wp.grid_x}, {wp.grid_y})"


@pytest.mark.asyncio
async def test_geojson_boundary_containment_and_endpoint_preservation():
    """Verify that every waypoint and connecting segment in emitted GeoJSON stays inside mission boundary."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req = {
            "region_id": "jezero_crater",
            "start": {"longitude": 77.0, "latitude": 18.2},
            "goal": {"longitude": 77.8, "latitude": 18.7},
            "options": {"profile": "balanced", "alternatives": 2}
        }
        resp = await ac.post("/api/routes/plan", json=req)
        assert resp.status_code == 200
        data = resp.json()

        # Check endpoint preservation and documented snapping
        assert data["original_start"]["longitude"] == 77.0
        assert data["original_start"]["latitude"] == 18.2
        assert data["start_snap_distance_m"] > 0
        assert data["original_goal"]["longitude"] == 77.8
        assert data["original_goal"]["latitude"] == 18.7
        assert data["goal_snap_distance_m"] > 0

        # Verify GeoJSON LineString coordinates
        features = data["geojson"]["features"]
        line_features = [f for f in features if f["geometry"]["type"] == "LineString"]
        assert len(line_features) >= 1

        for line in line_features:
            coords = line["geometry"]["coordinates"]
            # Start connector must match original start
            assert abs(coords[0][0] - 77.0) < 1e-4
            assert abs(coords[0][1] - 18.2) < 1e-4
            # End connector must match original goal
            assert abs(coords[-1][0] - 77.8) < 1e-4
            assert abs(coords[-1][1] - 18.7) < 1e-4

            # Every coordinate must remain inside mission exploration boundary
            for lon, lat, elev in coords:
                assert 77.0 <= lon <= 77.8, f"Longitude {lon} out of bounds"
                assert 18.2 <= lat <= 18.7, f"Latitude {lat} out of bounds"
                assert -3000 <= elev <= -1000, f"Elevation {elev} out of Jezero range"


@pytest.mark.asyncio
async def test_live_api_integration_corrected_dem():
    """Verify live API endpoints /api/terrain and /api/regions reflect the corrected DEM."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Check /api/terrain
        t_resp = await ac.get("/api/terrain?region_id=jezero_crater")
        assert t_resp.status_code == 200
        t_data = t_resp.json()
        assert t_data["status"] == "available"
        assert t_data["elevation"]["source_url"] == "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt44n000hb.lbl"

        # Check /api/regions
        r_resp = await ac.get("/api/regions")
        assert r_resp.status_code == 200
        r_data = r_resp.json()
        jezero = [r for r in r_data["regions"] if r["id"] == "jezero_crater"][0]
        assert jezero["elevation_range_m"]["min"] == -2719.0
        assert jezero["elevation_range_m"]["max"] == -1537.0
