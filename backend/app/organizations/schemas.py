import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.organizations.models import OrganizationStatus


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID
    status: OrganizationStatus
    created_at: datetime


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    key_prefix: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class APIKeyCreatedResponse(APIKeyResponse):
    api_key: str  # The raw API key returned ONLY on creation
