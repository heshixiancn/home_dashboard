import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def db_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def create_device(client):
    response = await client.post("/api/devices", json={"name": "NAS", "host": "10.126.126.10", "device_type": "NAS", "icon": "server", "description": "", "sort_order": 0})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_device_and_service_crud_url_update_and_favorite(client):
    device = await create_device(client)
    service_payload = {
        "device_id": device["id"],
        "name": "Docker",
        "protocol": "http",
        "port": 8080,
        "path": "ui",
        "custom_url": None,
        "icon": "globe",
        "description": "管理",
        "favorite": False,
        "enabled": True,
        "health_enabled": True,
        "health_method": "GET",
        "timeout_ms": 3000,
        "sort_order": 0,
    }
    response = await client.post("/api/services", json=service_payload)
    assert response.status_code == 201, response.text
    service = response.json()
    assert service["url"] == "http://10.126.126.10:8080/ui"

    response = await client.patch(f"/api/services/{service['id']}/favorite", json={"favorite": True})
    assert response.status_code == 200
    assert response.json()["favorite"] is True

    response = await client.put(f"/api/devices/{device['id']}", json={**device, "host": "10.126.126.11"})
    assert response.status_code == 200
    response = await client.get("/api/services")
    assert response.json()[0]["url"] == "http://10.126.126.11:8080/ui"

    response = await client.delete(f"/api/devices/{device['id']}")
    assert response.status_code == 409
    response = await client.delete(f"/api/devices/{device['id']}?cascade=true")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_health_endpoint_reports_database(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
