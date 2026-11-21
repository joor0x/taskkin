import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, verify_organization_access
from app.auth.models import User
from app.common.exceptions import NotFoundException
from app.infrastructure.database import get_db
from app.organizations.models import Organization
from app.organizations.schemas import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyResponse,
    OrganizationCreate,
    OrganizationResponse,
)
from app.organizations.service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post(
    "", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
async def create_organization(
    schema: OrganizationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(db)
    org = await service.create_organization(schema.name, current_user)
    return org


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(db)
    orgs = await service.list_user_organizations(current_user)
    return orgs


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    org: Annotated[Organization, Depends(verify_organization_access)],
):
    return org


@router.post(
    "/{organization_id}/api-keys",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    schema: APIKeyCreate,
    org: Annotated[Organization, Depends(verify_organization_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(db)
    api_key, raw_key = await service.create_api_key(org.id, schema.name)

    # We construct the response adding the raw_key
    response_data = APIKeyCreatedResponse(
        id=api_key.id,
        organization_id=api_key.organization_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        created_at=api_key.created_at,
        api_key=raw_key,
    )
    return response_data


@router.get("/{organization_id}/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    org: Annotated[Organization, Depends(verify_organization_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(db)
    api_keys = await service.list_api_keys(org.id)
    return api_keys


@router.delete(
    "/{organization_id}/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_api_key(
    api_key_id: uuid.UUID,
    org: Annotated[Organization, Depends(verify_organization_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(db)
    try:
        await service.revoke_api_key(org.id, api_key_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
