from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.payments.models import Wallet, WalletOwnerType


async def get_auth_headers(
    client: AsyncClient, email: str, role: str
) -> dict[str, str]:
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strongpassword123", "role": role},
    )
    login_res = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "strongpassword123"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_organization_lifecycle(client: AsyncClient):
    headers = await get_auth_headers(client, "requester_org@taskkin.local", "requester")

    # Create Organization
    create_res = await client.post(
        "/api/v1/organizations", json={"name": "ACME Corp"}, headers=headers
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    org_data = create_res.json()
    assert org_data["name"] == "ACME Corp"
    assert "id" in org_data

    # List Organizations
    list_res = await client.get("/api/v1/organizations", headers=headers)
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) >= 1
    assert list_res.json()[0]["id"] == org_data["id"]

    # Get Organization Details
    get_res = await client.get(
        f"/api/v1/organizations/{org_data['id']}", headers=headers
    )
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["name"] == "ACME Corp"


@pytest.mark.asyncio
async def test_api_keys_lifecycle(client: AsyncClient):
    headers = await get_auth_headers(
        client, "requester_keys@taskkin.local", "requester"
    )

    # Create Org
    org_res = await client.post(
        "/api/v1/organizations", json={"name": "Keys Org"}, headers=headers
    )
    org_id = org_res.json()["id"]

    # Create API Key
    key_res = await client.post(
        f"/api/v1/organizations/{org_id}/api-keys",
        json={"name": "Agent key"},
        headers=headers,
    )
    assert key_res.status_code == status.HTTP_201_CREATED
    key_data = key_res.json()
    assert key_data["name"] == "Agent key"
    assert "api_key" in key_data  # Should return raw key only on creation
    assert key_data["api_key"].startswith("tk_live_")

    # List API Keys
    list_res = await client.get(
        f"/api/v1/organizations/{org_id}/api-keys", headers=headers
    )
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == key_data["id"]

    # Revoke API Key
    revoke_res = await client.delete(
        f"/api/v1/organizations/{org_id}/api-keys/{key_data['id']}", headers=headers
    )
    assert revoke_res.status_code == status.HTTP_204_NO_CONTENT

    # List again (should be empty since it was revoked)
    list_res_after = await client.get(
        f"/api/v1/organizations/{org_id}/api-keys", headers=headers
    )
    assert len(list_res_after.json()) == 0


@pytest.mark.asyncio
async def test_worker_profile_lifecycle(client: AsyncClient):
    headers = await get_auth_headers(client, "worker_profile@taskkin.local", "worker")

    # Get Profile
    get_res = await client.get("/api/v1/workers/me", headers=headers)
    assert get_res.status_code == status.HTTP_200_OK
    profile = get_res.json()
    assert profile["display_name"] == "worker_profile"
    assert profile["verification_status"] == "unverified"

    # Update Profile (enforces location privacy approximation)
    update_payload = {
        "display_name": "Verified Developer",
        "bio": "Expert in QA testing",
        "country": "Spain",
        "city": "Madrid",
        "latitude_approx": 40.416775,  # Madrid exact is around 40.416775
        "longitude_approx": -3.703790,
        "languages": ["es", "en"],
        "skills": ["selenium", "playwright"],
    }
    patch_res = await client.patch(
        "/api/v1/workers/me", json=update_payload, headers=headers
    )
    assert patch_res.status_code == status.HTTP_200_OK
    updated = patch_res.json()
    assert updated["display_name"] == "Verified Developer"
    # Lat/Lon should be rounded to 3 decimal places
    assert updated["latitude_approx"] == 40.417
    assert updated["longitude_approx"] == -3.704
    assert updated["skills"] == ["selenium", "playwright"]


@pytest.mark.asyncio
async def test_pricing_estimate(client: AsyncClient):
    payload = {
        "estimated_minutes": 90,
        "complexity": "skilled",
        "hours_to_deadline": 24.0,
        "displacement_cost": "5.00",
    }
    response = await client.post("/api/v1/pricing/estimate", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # recommended_price = (estimated_hours * base_rate) * skill_mult * urgency_mult + displacement
    # hours = 1.5. base_rate = 15. base_cost = 22.50.
    # skill_mult = 1.25. urgency_mult = 1.15.
    # recommended = 22.50 * 1.25 * 1.15 + 5 = 32.34375 -> 32.34375 + 5 = 37.34
    assert data["recommended_price"] == "37.34"
    assert data["platform_fee"] == "5.60"  # 15% of 37.34 = 5.601 -> 5.60
    assert data["estimated_worker_payment"] == "31.74"  # 37.34 - 5.60 = 31.74


@pytest.mark.asyncio
async def test_task_lifecycle_and_moderation_rules(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await get_auth_headers(
        client, "requester_tasks@taskkin.local", "requester"
    )

    # Create Organization
    org_res = await client.post(
        "/api/v1/organizations", json={"name": "Tasks Org"}, headers=headers
    )
    org_id = org_res.json()["id"]

    # Setup wallet balance for organization to allow publication
    org_wallet_stmt = select(Wallet).where(
        Wallet.owner_type == WalletOwnerType.ORGANIZATION, Wallet.owner_id == org_id
    )
    res = await db_session.execute(org_wallet_stmt)
    org_wallet = res.scalar_one()
    org_wallet.available_balance = Decimal("1000.00")
    await db_session.commit()

    # 1. Create a safe task (decision = allow -> publishes directly to open)
    safe_payload = {
        "organization_id": org_id,
        "title": "Manual QA Website Testing",
        "description": "Test the checkout page flow and check for errors.",
        "category": "website_testing",
        "estimated_minutes": 30,
        "maximum_budget": "20.00",
        "deadline_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        "location_mode": "remote",
        "required_skills": ["qa", "testing"],
    }
    create_res = await client.post("/api/v1/tasks", json=safe_payload, headers=headers)
    assert create_res.status_code == status.HTTP_201_CREATED
    task_data = create_res.json()
    assert task_data["status"] == "draft"
    assert task_data["moderation"]["decision"] == "allow"
    assert task_data["safety_risk_level"] == "low"

    # Publish safe task -> transitions to open
    pub_res = await client.post(
        f"/api/v1/tasks/{task_data['id']}/publish", headers=headers
    )
    if pub_res.status_code != 200:
        print("PUBLISH ERROR DOMAIN:", pub_res.json())
    assert pub_res.status_code == status.HTTP_200_OK
    assert pub_res.json()["status"] == "open"
    assert pub_res.json()["published_at"] is not None

    # Cancel open task -> transitions to cancelled
    cancel_res = await client.post(
        f"/api/v1/tasks/{task_data['id']}/cancel", headers=headers
    )
    assert cancel_res.status_code == status.HTTP_200_OK
    assert cancel_res.json()["status"] == "cancelled"

    # 2. Create a borderline task (decision = manual_review -> publishes to pending_moderation)
    borderline_payload = safe_payload.copy()
    borderline_payload["title"] = (
        "Review account details page"  # Contains borderline keyword "account"
    )
    create_res = await client.post(
        "/api/v1/tasks", json=borderline_payload, headers=headers
    )
    task_data = create_res.json()
    assert task_data["moderation"]["decision"] == "manual_review"

    # Publish borderline task -> transitions to pending_moderation
    pub_res = await client.post(
        f"/api/v1/tasks/{task_data['id']}/publish", headers=headers
    )
    assert pub_res.status_code == status.HTTP_200_OK
    assert pub_res.json()["status"] == "pending_moderation"

    # 3. Create a prohibited task (decision = reject -> cannot publish, returns error)
    prohibited_payload = safe_payload.copy()
    prohibited_payload["title"] = (
        "Bypass captcha verification"  # Contains prohibited keyword "captcha"
    )
    create_res = await client.post(
        "/api/v1/tasks", json=prohibited_payload, headers=headers
    )
    task_data = create_res.json()
    assert task_data["moderation"]["decision"] == "reject"

    # Publish prohibited task -> fails with 409 Conflict
    pub_res = await client.post(
        f"/api/v1/tasks/{task_data['id']}/publish", headers=headers
    )
    assert pub_res.status_code == status.HTTP_409_CONFLICT
