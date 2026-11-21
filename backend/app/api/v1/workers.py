from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_worker
from app.auth.models import User
from app.common.exceptions import NotFoundException
from app.infrastructure.database import get_db
from app.reputation.service import ReputationService
from app.workers.schemas import WorkerProfileResponse, WorkerProfileUpdate
from app.workers.service import WorkerService

router = APIRouter(prefix="/workers", tags=["workers"])


class WorkerReputationResponse(BaseModel):
    quality_score: float
    reliability_score: float
    on_time_score: float
    instruction_score: float
    dispute_rate: float
    completed_tasks: int
    cancelled_tasks: int
    bayesian_score: float


@router.get("/me", response_model=WorkerProfileResponse)
async def get_worker_me(
    current_user: Annotated[User, Depends(require_worker)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = WorkerService(db)
    try:
        profile = await service.get_worker_profile_by_user_id(current_user.id)
        return profile
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.patch("/me", response_model=WorkerProfileResponse)
async def update_worker_me(
    schema: WorkerProfileUpdate,
    current_user: Annotated[User, Depends(require_worker)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = WorkerService(db)
    try:
        profile = await service.update_worker_profile(current_user.id, schema)
        return profile
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/me/assignments", response_model=list)
async def get_worker_assignments(
    current_user: Annotated[User, Depends(require_worker)],
):
    # Stub returning empty assignments list. Complete implementation in Fase 3.
    return []


@router.get("/me/reputation", response_model=WorkerReputationResponse)
async def get_worker_reputation(
    current_user: Annotated[User, Depends(require_worker)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = ReputationService(db)
    reputation = await service.calculate_worker_reputation(current_user.id)
    return reputation
