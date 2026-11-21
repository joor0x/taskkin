import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.assignments.models import AssignmentStatus


class TaskAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    worker_id: uuid.UUID
    status: AssignmentStatus
    accepted_at: datetime
    submitted_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
