"""Tests for NASA data sources, metadata, and terrain integrity."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.terrain_service import TerrainService


@pytest.mark.asyncio
async def test_region_metadata():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/regions")
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert len(data["regions"]) >= 1
        reg = data["regions"][0]
        assert reg["id"] == "jezero_crater"
        assert reg["name"] == "Jezero Crater"
        assert reg["bbox"]["min_lon"] == 77.0
        assert reg["bbox"]["max_lon"] == 77.8
        assert reg["bbox"]["min_lat"] == 18.2
        assert reg["bbox"]["max_lat"] == 18.7
        assert reg["crs"] == "EPSG:4326"
        assert "data_coverage" in reg
        assert reg["data_coverage"]["imagery"] == "available"


@pytest.mark.asyncio
async def test_layers_metadata_and_unavailability():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/layers?region_id=jezero_crater")
        assert response.status_code == 200
        data = response.json()
        assert data["region_id"] == "jezero_crater"
        assert "layers" in data
        layers = data["layers"]
        assert len(layers) > 0

        # Verify available layers have valid WMTS URL
        available_layers = [l for l in layers if l["status"] == "available"]
        assert len(available_layers) > 0
        for l in available_layers:
            assert l["url"] is not None
            assert "https://" in l["url"]
            assert len(l["limitations"]) > 0

        # Verify unavailable layers have null URL and clear limitation
        unavailable_layers = [l for l in layers if l["status"] == "unavailable"]
        assert len(unavailable_layers) > 0
        for l in unavailable_layers:
            assert l["url"] is None
            assert len(l["limitations"]) > 0


@pytest.mark.asyncio
async def test_observations_metadata_and_provenance():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/observations?region_id=jezero_crater")
        assert response.status_code == 200
        data = response.json()
        assert data["region_id"] == "jezero_crater"
        assert data["count"] == len(data["observations"])
        assert data["count"] > 0
        
        for obs in data["observations"]:
            assert "id" in obs
            assert "provenance" in obs
            assert obs["provenance"]["verification_status"] in ["verified", "simulated"]
            assert len(obs["provenance"]["limitations"]) > 0


def test_missing_terrain_does_not_fabricate_data():
    """Verify that when elevation data file is missing, empty arrays are returned without fabrication."""
    empty_terrain_svc = TerrainService(data_file_path="non_existent_file.npy")
    assert not empty_terrain_svc.is_available
    resp = empty_terrain_svc.get_terrain_response(region_id="jezero_crater")
    assert resp.status == "unavailable"
    assert resp.elevation.available is False
    assert resp.elevation.values == []
    assert resp.slope.available is False
    assert resp.slope.values == []
    assert resp.roughness.available is False
    assert resp.roughness.values == []
    assert len(resp.provenance.limitations) > 0
