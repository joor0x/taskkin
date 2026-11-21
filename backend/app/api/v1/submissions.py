import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.auth.models import User
from app.common.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.infrastructure.database import get_db
from app.submissions.schemas import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionReviewRequest,
)
from app.submissions.service import SubmissionService

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    schema: SubmissionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = SubmissionService(db)
    try:
        submission = await service.create_submission(schema, current_user)
        # Fetch detailed submission with evidence relationships loaded
        return await service.get_submission_by_id(submission.id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except BadRequestException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = SubmissionService(db)
    try:
        submission = await service.get_submission_by_id(submission_id)
        return submission
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/{submission_id}/approve", response_model=SubmissionResponse)
async def approve_submission(
    submission_id: uuid.UUID,
    schema: SubmissionReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = SubmissionService(db)
    try:
        submission = await service.approve_submission(
            submission_id=submission_id,
            reviewer=current_user,
            notes=schema.review_notes,
            quality_rating=schema.quality_rating,
            reliability_rating=schema.reliability_rating,
            on_time_rating=schema.on_time_rating,
            instruction_rating=schema.instruction_rating,
        )
        return await service.get_submission_by_id(submission.id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.post("/{submission_id}/reject", response_model=SubmissionResponse)
async def reject_submission(
    submission_id: uuid.UUID,
    schema: SubmissionReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = SubmissionService(db)
    try:
        submission = await service.reject_submission(
            submission_id, current_user, schema.review_notes
        )
        return await service.get_submission_by_id(submission.id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
