import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.assignments.schemas import TaskAssignmentResponse
from app.assignments.service import AssignmentService
from app.auth.models import User
from app.common.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.infrastructure.database import get_db

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("/{assignment_id}", response_model=TaskAssignmentResponse)
async def get_assignment(
    assignment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AssignmentService(db)
    try:
        assignment = await service.get_assignment_by_id(assignment_id)
        return assignment
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/{assignment_id}/cancel", response_model=TaskAssignmentResponse)
async def cancel_assignment(
    assignment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AssignmentService(db)
    try:
        assignment = await service.cancel_assignment(assignment_id, current_user)
        return assignment
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
