"""Tests ensuring API contract conformity across all endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_terrain_endpoint_contract():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/terrain?region_id=jezero_crater")
        assert resp.status_code == 200
        data = resp.json()
        assert data["region_id"] == "jezero_crater"
        assert "grid" in data
        assert data["grid"]["width"] == 103
        assert data["grid"]["height"] == 65
        assert data["grid"]["crs"] == "EPSG:4326"
        assert "elevation" in data
        assert data["elevation"]["unit"] == "meters"
        assert "slope" in data
        assert data["slope"]["unit"] == "degrees"
        assert "roughness" in data
        assert data["roughness"]["available"] is False
        assert "provenance" in data


@pytest.mark.asyncio
async def test_hazards_endpoint_contract():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/hazards?region_id=jezero_crater")
        assert resp.status_code == 200
        data = resp.json()
        assert data["region_id"] == "jezero_crater"
        assert "hazard_score" in data
        assert data["hazard_score"]["unit"] == "0-100"
        assert "hazard_types" in data
        assert len(data["hazard_types"]) > 0
        assert "provenance" in data


@pytest.mark.asyncio
async def test_missions_crud_contract():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create mission
        create_payload = {
            "region_id": "jezero_crater",
            "name": "Jezero traverse demo",
            "route_id": "route_test_123",
            "notes": "Testing integration contract"
        }
        resp = await ac.post("/api/missions", json=create_payload)
        assert resp.status_code == 201
        data = resp.json()
        mission_id = data["id"]
        assert mission_id.startswith("mission_")
        assert data["name"] == "Jezero traverse demo"
        assert data["route_id"] == "route_test_123"
        assert data["status"] == "draft"
        assert "summary" in data
        assert "report" in data
        assert len(data["report"]["sections"]) == 4

        # Retrieve created mission
        get_resp = await ac.get(f"/api/missions/{mission_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["id"] == mission_id
        assert get_data["name"] == "Jezero traverse demo"

        # 404 for missing mission
        missing_resp = await ac.get("/api/missions/mission_non_existent")
        assert missing_resp.status_code == 404
        err_data = missing_resp.json()
        assert "error" in err_data
        assert err_data["error"]["code"] == "NOT_FOUND"
