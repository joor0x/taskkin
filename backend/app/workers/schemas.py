import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.workers.models import AvailabilityStatus, VerificationStatus


class WorkerProfileUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=255)
    bio: str | None = Field(None, max_length=1000)
    country: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)
    latitude_approx: float | None = Field(None, ge=-90.0, le=90.0)
    longitude_approx: float | None = Field(None, ge=-180.0, le=180.0)
    languages: list[str] | None = None
    skills: list[str] | None = None
    availability_status: AvailabilityStatus | None = None


class WorkerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    bio: str | None
    country: str | None
    city: str | None
    latitude_approx: float | None
    longitude_approx: float | None
    languages: list[str]
    skills: list[str]
    verification_status: VerificationStatus
    availability_status: AvailabilityStatus
    created_at: datetime
    updated_at: datetime
