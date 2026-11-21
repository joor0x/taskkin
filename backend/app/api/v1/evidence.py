from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import require_worker
from app.auth.models import User
from app.common.exceptions import BadRequestException
from app.evidence.schemas import UploadURLRequest, UploadURLResponse
from app.evidence.service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("/upload-url", response_model=UploadURLResponse)
async def get_upload_url(
    schema: UploadURLRequest,
    current_user: Annotated[User, Depends(require_worker)],
):
    service = EvidenceService()
    try:
        response = await service.generate_upload_url(
            task_id=schema.task_id,
            file_name=schema.file_name,
            content_type=schema.content_type,
        )
        return response
    except BadRequestException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
