import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.auth.models import User, UserRole
from app.common.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.infrastructure.database import get_db
from app.organizations.models import OrganizationMember
from app.payments.models import Wallet, WalletOwnerType
from app.payments.schemas import (
    DepositRequest,
    LedgerEntryResponse,
    WalletResponse,
    WithdrawRequest,
)
from app.payments.service import WalletService
from app.workers.models import WorkerProfile

router = APIRouter(prefix="/payments", tags=["payments"])


async def check_wallet_access(
    wallet_id: uuid.UUID, user: User, db: AsyncSession
) -> Wallet:
    service = WalletService(db)
    wallet = await service.get_wallet_by_id(wallet_id)

    if user.role == UserRole.ADMIN:
        return wallet

    if wallet.owner_type == WalletOwnerType.WORKER:
        # Check if worker profile matches
        stmt = select(WorkerProfile).where(WorkerProfile.user_id == user.id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile or profile.id != wallet.owner_id:
            raise ForbiddenException("Access to this wallet is denied")

    elif wallet.owner_type == WalletOwnerType.ORGANIZATION:
        # Check if user is organization member
        stmt_org = select(OrganizationMember).where(
            OrganizationMember.organization_id == wallet.owner_id,
            OrganizationMember.user_id == user.id,
        )
        res = await db.execute(stmt_org)
        if not res.scalar_one_or_none():
            raise ForbiddenException("Access to this organization's wallet is denied")

    return wallet


@router.get("/wallets/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        wallet = await check_wallet_access(wallet_id, current_user, db)
        return wallet
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)


@router.post("/wallets/{wallet_id}/deposit", response_model=WalletResponse)
async def deposit_funds(
    wallet_id: uuid.UUID,
    schema: DepositRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        await check_wallet_access(wallet_id, current_user, db)
        service = WalletService(db)
        wallet = await service.deposit_funds(wallet_id, schema.amount, schema.reference)
        return wallet
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)


@router.post("/wallets/{wallet_id}/withdraw", response_model=WalletResponse)
async def withdraw_funds(
    wallet_id: uuid.UUID,
    schema: WithdrawRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        await check_wallet_access(wallet_id, current_user, db)
        service = WalletService(db)
        wallet = await service.withdraw_funds(
            wallet_id, schema.amount, schema.reference
        )
        return wallet
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.get("/wallets/{wallet_id}/ledger", response_model=list[LedgerEntryResponse])
async def get_wallet_ledger(
    wallet_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        await check_wallet_access(wallet_id, current_user, db)
        service = WalletService(db)
        entries = await service.get_ledger(wallet_id)
        return entries
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
