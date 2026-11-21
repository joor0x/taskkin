import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.infrastructure.celery import celery_app
from app.infrastructure.database import async_session_factory
from app.tasks.tasks import run_async
from app.webhooks.models import WebhookDelivery, WebhookDeliveryStatus


async def send_webhook_task_impl(
    delivery_id: uuid.UUID, max_retries: int = 3, attempt: int = 0, retry_func=None
) -> None:
    """Async core logic to deliver webhooks with HMAC signatures."""
    async with async_session_factory() as db:
        # Load delivery and eager load endpoint
        stmt = (
            select(WebhookDelivery)
            .options(selectinload(WebhookDelivery.endpoint))
            .where(WebhookDelivery.id == delivery_id)
        )
        res = await db.execute(stmt)
        delivery = res.scalar_one_or_none()
        if not delivery:
            return

        endpoint = delivery.endpoint
        if not endpoint or not endpoint.enabled:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.response_body = "Endpoint missing or disabled"
            await db.commit()
            return

        delivery.attempt_count += 1
        timestamp = int(datetime.now(UTC).timestamp())
        payload_str = json.dumps(delivery.payload, separators=(",", ":"))
        message = f"t={timestamp}.v1={payload_str}"

        # Compute signature
        signature = hmac.new(
            endpoint.secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-TaskKin-Signature": f"t={timestamp},v1={signature}",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint.url, content=payload_str, headers=headers
                )
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:4000]

                if 200 <= response.status_code < 300:
                    delivery.status = WebhookDeliveryStatus.SUCCESS
                else:
                    delivery.status = WebhookDeliveryStatus.FAILED
                    # Retry
                    if retry_func and attempt < max_retries:
                        db.add(delivery)
                        await db.commit()
                        retry_func(
                            exc=Exception(
                                f"Webhook failed with status {response.status_code}"
                            )
                        )
        except Exception as e:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.response_body = str(e)[:4000]
            if retry_func and attempt < max_retries:
                db.add(delivery)
                await db.commit()
                retry_func(exc=e)

        db.add(delivery)
        await db.commit()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)  # type: ignore[untyped-decorator]
def send_webhook_task(self, delivery_id: str) -> None:
    """Celery task to deliver webhooks with HMAC signatures."""
    uuid_id = uuid.UUID(delivery_id) if isinstance(delivery_id, str) else delivery_id
    run_async(
        send_webhook_task_impl(
            delivery_id=uuid_id,
            max_retries=self.max_retries,
            attempt=self.request.retries,
            retry_func=self.retry,
        )
    )
