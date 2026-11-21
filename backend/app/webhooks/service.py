import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException
from app.webhooks.models import WebhookDelivery, WebhookDeliveryStatus, WebhookEndpoint


class WebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_endpoint(self, org_id: uuid.UUID, url: str) -> WebhookEndpoint:
        secret = f"whsec_{secrets.token_hex(16)}"
        endpoint = WebhookEndpoint(
            organization_id=org_id, url=url, secret=secret, enabled=True
        )
        self.db.add(endpoint)
        await self.db.flush()
        return endpoint

    async def list_endpoints(self, org_id: uuid.UUID) -> list[WebhookEndpoint]:
        stmt = select(WebhookEndpoint).where(WebhookEndpoint.organization_id == org_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_endpoint(self, org_id: uuid.UUID, endpoint_id: uuid.UUID) -> None:
        stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id, WebhookEndpoint.organization_id == org_id
        )
        res = await self.db.execute(stmt)
        endpoint = res.scalar_one_or_none()
        if not endpoint:
            raise NotFoundException("Webhook endpoint not found")
        await self.db.delete(endpoint)
        await self.db.flush()

    async def trigger_event(
        self, org_id: uuid.UUID, event_type: str, payload: dict
    ) -> None:
        # Find enabled endpoints
        stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.organization_id == org_id, WebhookEndpoint.enabled
        )
        res = await self.db.execute(stmt)
        endpoints = res.scalars().all()

        for ep in endpoints:
            delivery = WebhookDelivery(
                webhook_endpoint_id=ep.id,
                event_type=event_type,
                payload=payload,
                status=WebhookDeliveryStatus.PENDING,
                attempt_count=0,
            )
            self.db.add(delivery)
            await self.db.flush()

            # Enqueue celery task for background delivery
            from app.webhooks.tasks import send_webhook_task

            send_webhook_task.delay(delivery.id)
