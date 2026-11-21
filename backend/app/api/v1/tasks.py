import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user_or_api_key
from app.assignments.schemas import TaskAssignmentResponse
from app.assignments.service import AssignmentService
from app.auth.models import User
from app.common.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.infrastructure.database import get_db
from app.organizations.models import Organization
from app.tasks.models import TaskCategory, TaskStatus
from app.tasks.schemas import TaskCreate, TaskResponse, TaskUpdate
from app.tasks.service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    schema: TaskCreate,
    auth_data: Annotated[
        tuple[User, Organization | None], Depends(get_current_user_or_api_key)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, api_org = auth_data

    # If authenticated via API Key, verify it matches the task's organization_id
    if api_org and api_org.id != schema.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key is not authorized for this organization",
        )

    service = TaskService(db)
    try:
        task = await service.create_task(schema, current_user)
        return task
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except BadRequestException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: TaskStatus | None = Query(None),
    category: TaskCategory | None = Query(None),
    country: str | None = Query(None),
    city: str | None = Query(None),
    minimum_price: Decimal | None = Query(None),
    maximum_price: Decimal | None = Query(None),
    required_skill: str | None = Query(None),
    deadline_before: datetime | None = Query(None),
):
    service = TaskService(db)
    tasks = await service.list_tasks(
        status=status,
        category=category,
        country=country,
        city=city,
        minimum_price=minimum_price,
        maximum_price=maximum_price,
        required_skill=required_skill,
        deadline_before=deadline_before,
    )

    # We must convert Task models to TaskResponse.
    # Note that TaskResponse here won't populate the pricing/moderation estimates since they are only evaluated for single detailed task view, which is normal behavior.
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = TaskService(db)
    try:
        task = await service.get_task_by_id(task_id)
        return task
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    schema: TaskUpdate,
    auth_data: Annotated[
        tuple[User, Organization | None], Depends(get_current_user_or_api_key)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, api_org = auth_data
    service = TaskService(db)

    # First fetch the task to verify organization if API key is used
    try:
        task_res = await service.get_task_by_id(task_id)
        if api_org and api_org.id != task_res.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key is not authorized for this organization",
            )

        task = await service.update_task(task_id, schema, current_user)
        return task
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except BadRequestException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.post("/{task_id}/publish", response_model=TaskResponse)
async def publish_task(
    task_id: uuid.UUID,
    auth_data: Annotated[
        tuple[User, Organization | None], Depends(get_current_user_or_api_key)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, api_org = auth_data
    service = TaskService(db)

    try:
        # Verify API key organization if used
        if api_org:
            task_res = await service.get_task_by_id(task_id)
            if api_org.id != task_res.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API Key is not authorized for this organization",
                )

        task = await service.publish_task(task_id, current_user)
        return task
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: uuid.UUID,
    auth_data: Annotated[
        tuple[User, Organization | None], Depends(get_current_user_or_api_key)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, api_org = auth_data
    service = TaskService(db)

    try:
        # Verify API key organization if used
        if api_org:
            task_res = await service.get_task_by_id(task_id)
            if api_org.id != task_res.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API Key is not authorized for this organization",
                )

        task = await service.cancel_task(task_id, current_user)
        return task
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.post("/{task_id}/claim", response_model=TaskAssignmentResponse)
async def claim_task(
    task_id: uuid.UUID,
    auth_data: Annotated[
        tuple[User, Organization | None], Depends(get_current_user_or_api_key)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Retrieve user from auth tuple (claims must be made by an authenticated worker user)
    user, _ = auth_data
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    service = AssignmentService(db)
    try:
        assignment = await service.claim_task(task_id, user)
        return assignment
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
