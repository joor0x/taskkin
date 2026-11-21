from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.payments.models import Wallet, WalletOwnerType
from app.tasks.models import Task
from app.tasks.tasks import check_expired_tasks


async def get_auth_headers(
    client: AsyncClient, email: str, role: str
) -> dict[str, str]:
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
async def test_claim_and_submission_lifecycle(
    client: AsyncClient, db_session: AsyncSession
):
    # Register/Login Requester and Worker
    req_headers = await get_auth_headers(
        client, "requester_flow@taskkin.local", "requester"
    )
    work_headers = await get_auth_headers(client, "worker_flow@taskkin.local", "worker")

    # Create Organization
    org_res = await client.post(
        "/api/v1/organizations", json={"name": "Flow Org"}, headers=req_headers
    )
    org_id = org_res.json()["id"]

    # Initial wallets setup (ensure org has balance for testing payouts)
    # We load the org wallet and add balance
    org_wallet_stmt = select(Wallet).where(
        Wallet.owner_type == WalletOwnerType.ORGANIZATION, Wallet.owner_id == org_id
    )
    res = await db_session.execute(org_wallet_stmt)
    org_wallet = res.scalar_one()
    org_wallet.available_balance = Decimal("50.00")
    org_wallet.reserved_balance = Decimal("10.00")  # simulate task escrow
    await db_session.commit()

    # Create and publish task
    task_payload = {
        "organization_id": org_id,
        "title": "QA Test Submission Flow",
        "description": "Test the submission and approval flow in backend.",
        "category": "website_testing",
        "estimated_minutes": 30,
        "maximum_budget": "20.00",
        "deadline_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "location_mode": "remote",
        "required_skills": ["qa"],
    }
    create_res = await client.post(
        "/api/v1/tasks", json=task_payload, headers=req_headers
    )
    task_id = create_res.json()["id"]

    pub_res = await client.post(f"/api/v1/tasks/{task_id}/publish", headers=req_headers)
    assert pub_res.status_code == status.HTTP_200_OK

    # 1. Claim task (Worker claims)
    claim_res = await client.post(
        f"/api/v1/tasks/{task_id}/claim", headers=work_headers
    )
    assert claim_res.status_code == status.HTTP_200_OK
    assignment = claim_res.json()
    assert assignment["status"] == "active"
    assert "id" in assignment
    assignment_id = assignment["id"]

    # Verify task state is now ASSIGNED
    task_res = await client.get(f"/api/v1/tasks/{task_id}")
    assert task_res.json()["status"] == "assigned"

    # 2. Get upload URL for evidence
    upload_payload = {
        "file_name": "screenshot.png",
        "content_type": "image/png",
        "task_id": task_id,
    }
    upload_res = await client.post(
        "/api/v1/evidence/upload-url", json=upload_payload, headers=work_headers
    )
    assert upload_res.status_code == status.HTTP_200_OK
    url_data = upload_res.json()
    assert "upload_url" in url_data
    assert url_data["evidence_key"].endswith("screenshot.png")

    # 3. Create Submission
    sub_payload = {
        "assignment_id": assignment_id,
        "text_result": "I completed the QA test. The checkout works.",
        "evidences": [
            {
                "evidence_type": "image",
                "storage_key": url_data["evidence_key"],
                "file_name": "screenshot.png",
                "mime_type": "image/png",
                "file_size": 120450,
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "metadata_json": {},
            }
        ],
    }
    sub_res = await client.post(
        "/api/v1/submissions", json=sub_payload, headers=work_headers
    )
    assert sub_res.status_code == status.HTTP_201_CREATED
    submission = sub_res.json()
    assert submission["status"] == "pending"
    assert len(submission["evidence"]) == 1
    submission_id = submission["id"]

    # Verify task state is now SUBMITTED
    task_res = await client.get(f"/api/v1/tasks/{task_id}")
    assert task_res.json()["status"] == "submitted"

    # 4. Reject Submission (Requester rejects)
    reject_res = await client.post(
        f"/api/v1/submissions/{submission_id}/reject",
        json={"review_notes": "Screenshot is missing details"},
        headers=req_headers,
    )
    assert reject_res.status_code == status.HTTP_200_OK
    assert reject_res.json()["status"] == "rejected"

    # Verify assignment goes back to active and task back to assigned
    assign_get = await client.get(f"/api/v1/assignments/{assignment_id}")
    assert assign_get.json()["status"] == "active"
    task_res = await client.get(f"/api/v1/tasks/{task_id}")
    assert task_res.json()["status"] == "assigned"

    # 5. Resubmit Task (Worker submits again)
    sub_res_2 = await client.post(
        "/api/v1/submissions", json=sub_payload, headers=work_headers
    )
    assert sub_res_2.status_code == status.HTTP_201_CREATED
    submission_2_id = sub_res_2.json()["id"]

    # 6. Approve Submission
    approve_res = await client.post(
        f"/api/v1/submissions/{submission_2_id}/approve",
        json={"review_notes": "Great job, payout released"},
        headers=req_headers,
    )
    assert approve_res.status_code == status.HTTP_200_OK
    assert approve_res.json()["status"] == "approved"

    # Verify task status is APPROVED, assignment status is completed
    task_res = await client.get(f"/api/v1/tasks/{task_id}")
    assert task_res.json()["status"] == "approved"
    assign_get = await client.get(f"/api/v1/assignments/{assignment_id}")
    assert assign_get.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_celery_task_expiration(client: AsyncClient, db_session: AsyncSession):
    # Register/Login
    req_headers = await get_auth_headers(
        client, "requester_exp@taskkin.local", "requester"
    )

    # Create Org
    org_res = await client.post(
        "/api/v1/organizations", json={"name": "Exp Org"}, headers=req_headers
    )
    org_id = org_res.json()["id"]

    # Setup wallet balance for organization to allow publication
    org_wallet_stmt = select(Wallet).where(
        Wallet.owner_type == WalletOwnerType.ORGANIZATION, Wallet.owner_id == org_id
    )
    res = await db_session.execute(org_wallet_stmt)
    org_wallet = res.scalar_one()
    org_wallet.available_balance = Decimal("100.00")
    await db_session.commit()

    # Create task with a deadline in the past
    task_payload = {
        "organization_id": org_id,
        "title": "Expired Task Test",
        "description": "This task should expire immediately when celery task runs.",
        "category": "website_testing",
        "estimated_minutes": 30,
        "maximum_budget": "10.00",
        "deadline_at": (
            datetime.now(UTC) - timedelta(minutes=5)
        ).isoformat(),  # In the past!
        "location_mode": "remote",
        "required_skills": ["qa"],
    }
    # Direct database create to bypass FastAPI validation of deadline in future if needed,
    # or we can update it in the database after creation!
    # Let's create it as draft first with deadline in future:
    task_payload["deadline_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    create_res = await client.post(
        "/api/v1/tasks", json=task_payload, headers=req_headers
    )
    task_id = create_res.json()["id"]

    pub_res = await client.post(f"/api/v1/tasks/{task_id}/publish", headers=req_headers)
    if pub_res.status_code != 200:
        print("PUBLISH ERROR:", pub_res.json())
    assert pub_res.status_code == status.HTTP_200_OK

    # Update task in DB to set deadline in the past
    stmt = select(Task).where(Task.id == task_id)
    res = await db_session.execute(stmt)
    db_task = res.scalar_one()
    db_task.deadline_at = datetime.now(UTC) - timedelta(minutes=5)
    await db_session.commit()

    # Verify status is still open
    task_res = await client.get(f"/api/v1/tasks/{task_id}")
    assert task_res.json()["status"] == "open"

    # Run the Celery task synchronously
    check_expired_tasks()

    # Expire identity map cache so client.get reads updated values from PostgreSQL
    db_session.expire_all()

    # Re-fetch database session to check task status
    # Wait, client.get makes a new HTTP request which queries the database directly
    task_res = await client.get(f"/api/v1/tasks/{task_id}")
    assert task_res.json()["status"] == "expired"
