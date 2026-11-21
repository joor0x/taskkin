import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.webhooks.models import WebhookDeliveryStatus


class WebhookEndpointCreate(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000)


class WebhookEndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    url: str
    secret: str
    enabled: bool
    created_at: datetime


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    webhook_endpoint_id: uuid.UUID
    event_type: str
    payload: dict
    status: WebhookDeliveryStatus
    attempt_count: int
    next_attempt_at: datetime | None
    response_status: int | None
    response_body: str | None
    created_at: datetime
