import uuid

from pydantic import BaseModel, Field


class UploadURLRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=3, max_length=100)
    task_id: uuid.UUID


class UploadURLResponse(BaseModel):
    upload_url: str
    download_url: str
    evidence_key: str
