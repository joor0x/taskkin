import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    payload = {
        "email": "worker_test@taskkin.local",
        "password": "strongpassword123",
        "role": "worker",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "worker_test@taskkin.local"
    assert data["role"] == "worker"
    assert "id" in data
    assert "status" in data
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_register_duplicate_user(client: AsyncClient):
    payload = {
        "email": "duplicate_test@taskkin.local",
        "password": "strongpassword123",
        "role": "worker",
    }
    # Register first time
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    # Register second time
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register user first
    payload = {
        "email": "login_test@taskkin.local",
        "password": "strongpassword123",
        "role": "worker",
    }
    await client.post("/api/v1/auth/register", json=payload)

    # Login
    login_payload = {
        "email": "login_test@taskkin.local",
        "password": "strongpassword123",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    payload = {
        "email": "wrong_password_test@taskkin.local",
        "password": "strongpassword123",
        "role": "worker",
    }
    await client.post("/api/v1/auth/register", json=payload)

    # Login with wrong password
    login_payload = {
        "email": "wrong_password_test@taskkin.local",
        "password": "wrongpassword",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    # Register and Login
    payload = {
        "email": "refresh_test@taskkin.local",
        "password": "strongpassword123",
        "role": "worker",
    }
    await client.post("/api/v1/auth/register", json=payload)

    login_payload = {
        "email": "refresh_test@taskkin.local",
        "password": "strongpassword123",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # Refresh token
    refresh_payload = {"refresh_token": refresh_token}
    response = await client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["access_token"] != tokens["access_token"]  # Should be a new token


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    payload = {
        "email": "me_test@taskkin.local",
        "password": "strongpassword123",
        "role": "worker",
    }
    await client.post("/api/v1/auth/register", json=payload)

    login_payload = {"email": "me_test@taskkin.local", "password": "strongpassword123"}
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    access_token = login_res.json()["access_token"]

    # Get /me
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "me_test@taskkin.local"
