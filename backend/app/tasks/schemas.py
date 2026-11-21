import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.tasks.models import LocationMode, TaskCategory, TaskStatus


class TaskCreate(BaseModel):
    organization_id: uuid.UUID
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10, max_length=5000)
    category: TaskCategory
    estimated_minutes: int = Field(..., ge=1)
    maximum_budget: Decimal = Field(..., ge=0)
    currency: str = Field("EUR", min_length=3, max_length=3)
    deadline_at: datetime
    location_mode: LocationMode = LocationMode.REMOTE
    country: str | None = None
    city: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    required_languages: list[str] = Field(default_factory=list)
    evidence_requirements: list[dict] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=255)
    description: str | None = Field(None, min_length=10, max_length=5000)
    category: TaskCategory | None = None
    estimated_minutes: int | None = Field(None, ge=1)
    maximum_budget: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    deadline_at: datetime | None = None
    location_mode: LocationMode | None = None
    country: str | None = None
    city: str | None = None
    required_skills: list[str] | None = None
    required_languages: list[str] | None = None
    evidence_requirements: list[dict] | None = None


class TaskResponsePricing(BaseModel):
    recommended_price: Decimal
    minimum_price: Decimal


class TaskResponseModeration(BaseModel):
    decision: str
    risk_level: str


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_by_user_id: uuid.UUID
    title: str
    description: str
    category: TaskCategory
    status: TaskStatus
    currency: str
    offered_price: Decimal
    maximum_budget: Decimal
    estimated_minutes: int
    deadline_at: datetime
    location_mode: LocationMode
    country: str | None
    city: str | None
    required_skills: list[str]
    required_languages: list[str]
    evidence_requirements: list[dict]
    safety_risk_level: str
    moderation_status: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None

    # Nested pricing & moderation estimates (optional)
    pricing: TaskResponsePricing | None = None
    moderation: TaskResponseModeration | None = None
