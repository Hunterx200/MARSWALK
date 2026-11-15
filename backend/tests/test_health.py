"""Tests for health endpoint."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "marswalk-backend"
        assert "version" in data
        assert "time_utc" in data
        assert "dependencies" in data
        assert "route_engine" in data["dependencies"]
        assert data["dependencies"]["route_engine"] == "available"
