"""Tests for authorization and admin access."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_course_requires_admin(client: AsyncClient, auth_headers):
    """Regular users cannot create courses."""
    response = await client.post("/api/v1/courses", json={
        "title": "Test Course",
        "description": "A test course",
    }, headers=auth_headers)
    assert response.status_code == 403
    assert "Admin privileges required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_lab_requires_admin(client: AsyncClient, auth_headers):
    """Regular users cannot create labs."""
    response = await client.post("/api/v1/labs", json={
        "title": "Test Lab",
        "description": "A test lab",
        "infrastructure_spec": {},
    }, headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_courses_requires_auth(client: AsyncClient):
    """Listing courses requires authentication."""
    response = await client.get("/api/v1/courses")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_labs_requires_auth(client: AsyncClient):
    """Listing labs requires authentication."""
    response = await client.get("/api/v1/labs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_courses_authenticated(client: AsyncClient, auth_headers):
    """Authenticated users can list their courses."""
    response = await client.get("/api/v1/courses", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_labs_authenticated(client: AsyncClient, auth_headers):
    """Authenticated users can list their labs."""
    response = await client.get("/api/v1/labs", headers=auth_headers)
    assert response.status_code == 200
