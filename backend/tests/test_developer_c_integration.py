"""Integration tests verifying Developer C's AlternativeRoutePlanner inside MARSWALK backend."""
import pytest
from httpx import AsyncClient, ASGITransport
import numpy as np

from app.main import app
from app.services.route_service import route_service
from algorithms.routing.alternatives import AlternativeRoutePlanner


def test_backend_uses_developer_c_planner_instance():
    """Verify that route_service uses Developer C's AlternativeRoutePlanner directly."""
    assert route_service._planner is not None
    assert isinstance(route_service._planner, AlternativeRoutePlanner)
    
    # Verify actual NASA MOLA DEM (65x103), NOT a synthetic benchmark grid (80x80 or 100x100)
    dem = route_service._planner.dem
    assert dem.shape == (65, 103)
    assert dem.min() < -1000  # Jezero floor is around -1127m
    assert dem.max() > 1000   # Jezero rim reaches +1145m
    assert route_service._planner.resolution_m == 463.0
    assert route_service._planner.hazard_mask.shape == (65, 103)
    assert route_service._planner.hazard_mask.sum() > 0


@pytest.mark.asyncio
async def test_all_three_profiles_direct_balanced_safe():
    """Verify all three routing profiles: direct, balanced, and safe."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        profiles = ["direct", "balanced", "safe"]
        results = {}

        for prof in profiles:
            req = {
                "region_id": "jezero_crater",
                "start": {"longitude": 77.35, "latitude": 18.45},
                "goal": {"longitude": 77.55, "latitude": 18.55},
                "options": {
                    "profile": prof,
                    "max_slope_degrees": 25.0,
                    "avoid_hazards": True,
                    "alternatives": 2,
                }
            }
            resp = await ac.post("/api/routes/plan", json=req)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            primary = data["routes"][0]
            assert primary["profile"] == prof
            assert primary["distance_meters"] > 0
            assert len(primary["path"]) > 0
            results[prof] = primary

        # Direct route should be shorter than or equal to safe route
        assert results["direct"]["distance_meters"] <= results["safe"]["distance_meters"]
        # Safe route should have lower or equal risk score compared to direct route
        assert results["safe"]["risk_score"] <= results["direct"]["risk_score"]


@pytest.mark.asyncio
async def test_output_coordinates_match_jezero_boundaries():
    """Verify that every generated waypoint falls strictly inside the Jezero Crater boundaries."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req = {
            "region_id": "jezero_crater",
            "start": {"longitude": 77.30, "latitude": 18.35},
            "goal": {"longitude": 77.60, "latitude": 18.60},
            "options": {"profile": "balanced", "alternatives": 2}
        }
        resp = await ac.post("/api/routes/plan", json=req)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["routes"]) >= 1

        for route in data["routes"]:
            for node in route["path"]:
                assert 77.0 <= node["longitude"] <= 77.8
                assert 18.2 <= node["latitude"] <= 18.7
                assert 0 <= node["row"] < 65
                assert 0 <= node["column"] < 103


@pytest.mark.asyncio
async def test_frontend_geojson_and_comparison_contract():
    """Verify GeoJSON FeatureCollection and comparison metrics for Developer A frontend."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req = {
            "region_id": "jezero_crater",
            "start": {"longitude": 77.35, "latitude": 18.45},
            "goal": {"longitude": 77.55, "latitude": 18.55},
            "options": {"profile": "balanced", "alternatives": 2}
        }
        resp = await ac.post("/api/routes/plan", json=req)
        assert resp.status_code == 200
        data = resp.json()
        
        # GeoJSON contract
        assert "geojson" in data
        assert data["geojson"] is not None
        assert data["geojson"]["type"] == "FeatureCollection"
        features = data["geojson"]["features"]
        assert len(features) > 0
        
        # At least one LineString feature for the route trajectory
        line_features = [f for f in features if f["geometry"]["type"] == "LineString"]
        assert len(line_features) >= 1
        line = line_features[0]
        assert len(line["geometry"]["coordinates"]) > 0
        assert "properties" in line
        assert "profile" in line["properties"]
        
        # Comparison metrics
        assert "comparison" in data
        assert data["comparison"] is not None
        assert len(data["comparison"]) >= 2
        for comp in data["comparison"]:
            assert "profile" in comp
            assert "distance_m" in comp
            assert "estimated_risk_score" in comp


@pytest.mark.asyncio
async def test_grid_coordinates_input_supported():
    """Verify algorithm testing with grid indices (start_x, start_y, goal_x, goal_y)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req = {
            "region_id": "jezero_crater",
            "start_x": 45,
            "start_y": 32,
            "goal_x": 65,
            "goal_y": 25,
            "profile": "safe"
        }
        resp = await ac.post("/api/routes/plan", json=req)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["routes"]) >= 1
        primary = data["routes"][0]
        assert primary["profile"] == "safe"
