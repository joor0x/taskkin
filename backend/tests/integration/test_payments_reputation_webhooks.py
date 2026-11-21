import hashlib
import hmac
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.payments.models import Wallet, WalletOwnerType
from app.tasks.models import Task
from app.webhooks.models import WebhookDelivery, WebhookDeliveryStatus
from app.webhooks.tasks import send_webhook_task_impl


async def get_auth_headers(
    client: AsyncClient, email: str, role: str
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepassword123", "role": role},
    )
    login_res = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "securepassword123"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_payments_reputation_and_escrow_workflow(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Create users
    req_headers = await get_auth_headers(client, "req_pay@taskkin.local", "requester")
    work_headers = await get_auth_headers(client, "work_pay@taskkin.local", "worker")

    # 2. Create organization
    org_res = await client.post(
        "/api/v1/organizations", json={"name": "Finance Org"}, headers=req_headers
    )
    org_id = org_res.json()["id"]

    # 3. Retrieve organization wallet
    # Org wallets are automatically created. Let's find it.
    stmt = select(Wallet).where(
        Wallet.owner_type == WalletOwnerType.ORGANIZATION, Wallet.owner_id == org_id
    )
    res = await db_session.execute(stmt)
    org_wallet = res.scalar_one()

    # 4. Deposit funds via API
    deposit_payload = {"amount": 150.00, "reference": "Initial funding"}
    dep_res = await client.post(
        f"/api/v1/payments/wallets/{org_wallet.id}/deposit",
        json=deposit_payload,
        headers=req_headers,
    )
    assert dep_res.status_code == status.HTTP_200_OK
    assert float(dep_res.json()["available_balance"]) == 150.00

    # 5. Create task
    task_payload = {
        "organization_id": org_id,
        "title": "Paid Quality Survey",
        "description": "Provide detailed feedback on UI aesthetics.",
        "category": "website_testing",
        "offered_price": 40.00,
        "maximum_budget": 50.00,
        "estimated_minutes": 30,
        "deadline_at": "2030-01-01T00:00:00Z",
        "location_mode": "remote",
        "required_skills": ["ux"],
    }
    create_res = await client.post(
        "/api/v1/tasks", json=task_payload, headers=req_headers
    )
    task_id = create_res.json()["id"]

    # 6. Publish task -> should trigger escrow reservation!
    pub_res = await client.post(f"/api/v1/tasks/{task_id}/publish", headers=req_headers)
    assert pub_res.status_code == status.HTTP_200_OK

    # Verify wallet balances after reservation
    await db_session.refresh(org_wallet)
    db_task_stmt = select(Task).where(Task.id == task_id)
    db_task_res = await db_session.execute(db_task_stmt)
    db_task = db_task_res.scalar_one()
    offered_price = db_task.offered_price

    assert org_wallet.available_balance == Decimal("150.00") - offered_price
    assert org_wallet.reserved_balance == offered_price

    # 7. Claim and submit task
    claim_res = await client.post(
        f"/api/v1/tasks/{task_id}/claim", headers=work_headers
    )
    assert claim_res.status_code == status.HTTP_200_OK
    assignment_id = claim_res.json()["id"]

    sub_payload = {
        "assignment_id": assignment_id,
        "text_result": "Quality is outstanding, very modern design.",
        "evidences": [],
    }
    sub_res = await client.post(
        "/api/v1/submissions", json=sub_payload, headers=work_headers
    )
    assert sub_res.status_code == status.HTTP_201_CREATED
    submission_id = sub_res.json()["id"]

    # 8. Approve submission with custom quality metrics
    approve_payload = {
        "review_notes": "Perfect execution!",
        "quality_rating": 5.0,
        "reliability_rating": 5.0,
        "on_time_rating": 4.0,
        "instruction_rating": 5.0,
    }
    app_res = await client.post(
        f"/api/v1/submissions/{submission_id}/approve",
        json=approve_payload,
        headers=req_headers,
    )
    assert app_res.status_code == status.HTTP_200_OK

    # 9. Verify payout distribution
    platform_fee = (offered_price * Decimal("0.15")).quantize(Decimal("0.01"))
    worker_payout = offered_price - platform_fee

    await db_session.refresh(org_wallet)
    assert org_wallet.reserved_balance == Decimal("0.00")
    assert org_wallet.available_balance == Decimal("150.00") - offered_price

    # Fetch worker wallet
    stmt_worker = select(Wallet).where(Wallet.owner_type == WalletOwnerType.WORKER)
    res_worker = await db_session.execute(stmt_worker)
    worker_wallet = res_worker.scalars().first()
    assert worker_wallet.available_balance == worker_payout

    # 10. Verify worker reputation calculation
    rep_res = await client.get("/api/v1/workers/me/reputation", headers=work_headers)
    assert rep_res.status_code == status.HTTP_200_OK
    rep_data = rep_res.json()
    assert rep_data["quality_score"] == 5.0
    assert rep_data["reliability_score"] == 5.0
    assert rep_data["on_time_score"] == 4.0
    assert rep_data["instruction_score"] == 5.0
    assert rep_data["completed_tasks"] == 1
    # Bayesian score: C=5, m=4. R = (5+5+4+5)/4 = 4.75. Score = (5*4 + 1*4.75)/6 = 24.75 / 6 = 4.125 -> 4.13
    assert rep_data["bayesian_score"] == 4.12


@pytest.mark.asyncio
async def test_webhooks_configuration_and_signatures(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Setup users
    req_headers = await get_auth_headers(client, "req_web@taskkin.local", "requester")

    # 2. Create organization
    org_res = await client.post(
        "/api/v1/organizations", json={"name": "Webhooks Org"}, headers=req_headers
    )
    org_id = org_res.json()["id"]

    # 3. Configure webhook endpoint via API
    endpoint_payload = {"url": "https://callback.example.com/webhook"}
    create_res = await client.post(
        f"/api/v1/organizations/{org_id}/webhooks",
        json=endpoint_payload,
        headers=req_headers,
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    data = create_res.json()
    assert data["url"] == "https://callback.example.com/webhook"
    assert data["secret"].startswith("whsec_")
    webhook_id = data["id"]
    webhook_secret = data["secret"]

    # 4. List webhook endpoints
    list_res = await client.get(
        f"/api/v1/organizations/{org_id}/webhooks", headers=req_headers
    )
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == webhook_id

    # 5. Test Webhook Delivery and Signature calculation
    delivery = WebhookDelivery(
        webhook_endpoint_id=webhook_id,
        event_type="test.event",
        payload={"ping": "pong"},
        status=WebhookDeliveryStatus.PENDING,
    )
    db_session.add(delivery)
    await db_session.commit()

    # Mock post call inside send_webhook_task
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Execute async webhook delivery directly
        await send_webhook_task_impl(delivery.id)

        # Refresh from database and check status
        await db_session.refresh(delivery)
        assert delivery.status == WebhookDeliveryStatus.SUCCESS
        assert delivery.response_status == 200
        assert delivery.response_body == "OK"

        # Verify mock post signature headers
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        called_url = args[0]
        called_content = kwargs["content"]
        called_headers = kwargs["headers"]

        assert called_url == "https://callback.example.com/webhook"
        assert called_content == '{"ping":"pong"}'
        assert "X-TaskKin-Signature" in called_headers

        # Verify HMAC signature match
        sig_header = called_headers["X-TaskKin-Signature"]
        # Format: t=1234567,v1=signature
        parts = {p.split("=")[0]: p.split("=")[1] for p in sig_header.split(",")}
        timestamp = parts["t"]
        v1_sig = parts["v1"]

        expected_msg = f"t={timestamp}.v1={called_content}"
        expected_sig = hmac.new(
            webhook_secret.encode(), expected_msg.encode(), hashlib.sha256
        ).hexdigest()

        assert v1_sig == expected_sig

    # 6. Delete webhook endpoint
    del_res = await client.delete(
        f"/api/v1/organizations/{org_id}/webhooks/{webhook_id}", headers=req_headers
    )
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # List again to verify it is gone
    list_res = await client.get(
        f"/api/v1/organizations/{org_id}/webhooks", headers=req_headers
    )
    assert len(list_res.json()) == 0
