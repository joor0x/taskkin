import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import verify_organization_access
from app.common.exceptions import NotFoundException
from app.infrastructure.database import get_db
from app.organizations.models import Organization
from app.webhooks.schemas import WebhookEndpointCreate, WebhookEndpointResponse
from app.webhooks.service import WebhookService

router = APIRouter(
    prefix="/organizations/{organization_id}/webhooks", tags=["webhooks"]
)


@router.post(
    "", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED
)
async def create_webhook(
    organization_id: uuid.UUID,
    schema: WebhookEndpointCreate,
    org: Annotated[Organization, Depends(verify_organization_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = WebhookService(db)
    endpoint = await service.create_endpoint(org.id, schema.url)
    return endpoint


@router.get("", response_model=list[WebhookEndpointResponse])
async def list_webhooks(
    organization_id: uuid.UUID,
    org: Annotated[Organization, Depends(verify_organization_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = WebhookService(db)
    endpoints = await service.list_endpoints(org.id)
    return endpoints


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    organization_id: uuid.UUID,
    webhook_id: uuid.UUID,
    org: Annotated[Organization, Depends(verify_organization_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = WebhookService(db)
    try:
        await service.delete_endpoint(org.id, webhook_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
