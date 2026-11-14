"""Tests for route planning and coordinates validation."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_route_planning_valid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req = {
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
                "avoid_hazards": True,
                "hazard_weight": 0.4,
                "slope_weight": 0.3,
                "distance_weight": 0.3,
                "alternatives": 2
            }
        }
        resp = await ac.post("/api/routes/plan", json=req)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["region_id"] == "jezero_crater"
        assert "request_id" in data
        assert len(data["routes"]) >= 1
        
        primary = data["routes"][0]
        assert primary["label"] == "Primary route"
        assert primary["distance_meters"] > 0
        assert primary["estimated_travel_time_minutes"] > 0
        assert len(primary["path"]) > 0
        assert "risk_level" in primary
        assert primary["risk_level"] in ["low", "medium", "high"]
        
        # Verify node structure has both geographic and grid indices
        first_node = primary["path"][0]
        assert "longitude" in first_node
        assert "latitude" in first_node
        assert "row" in first_node
        assert "column" in first_node
        
        assert "provenance" in primary
        assert "cost_model" in primary["provenance"]
        assert len(primary["provenance"]["limitations"]) > 0


@pytest.mark.asyncio
async def test_route_planning_rejects_out_of_bounds_coordinates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req = {
            "region_id": "jezero_crater",
            "start": {
                "longitude": 10.0,  # Well outside Jezero (77.0 - 77.8)
                "latitude": 18.45
            },
            "goal": {
                "longitude": 77.55,
                "latitude": 18.55
            }
        }
        resp = await ac.post("/api/routes/plan", json=req)
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_REQUEST"
        assert "outside the Jezero Crater region" in data["error"]["message"]
