import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.evidence.models import EvidenceType
from app.submissions.models import SubmissionStatus


class EvidenceCreate(BaseModel):
    evidence_type: EvidenceType
    storage_key: str
    file_name: str
    mime_type: str
    file_size: int
    sha256: str
    metadata_json: dict = {}


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    submission_id: uuid.UUID
    evidence_type: EvidenceType
    storage_key: str
    file_name: str
    mime_type: str
    file_size: int
    sha256: str
    metadata_json: dict
    created_at: datetime


class SubmissionCreate(BaseModel):
    assignment_id: uuid.UUID
    text_result: str | None = None
    structured_result: dict | None = None
    evidences: list[EvidenceCreate] = []


class SubmissionReviewRequest(BaseModel):
    review_notes: str | None = None
    quality_rating: float | None = None
    reliability_rating: float | None = None
    on_time_rating: float | None = None
    instruction_rating: float | None = None


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assignment_id: uuid.UUID
    worker_id: uuid.UUID
    text_result: str | None
    structured_result: dict | None
    status: SubmissionStatus
    submitted_at: datetime
    reviewed_at: datetime | None
    review_notes: str | None
    evidence: list[EvidenceResponse] = []
