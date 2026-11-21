from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.auth.models import User
from app.auth.schemas import Token, UserLogin, UserRegister, UserResponse
from app.auth.service import AuthService
from app.common.exceptions import ConflictException, UnauthorizedException
from app.infrastructure.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    schema: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    try:
        user = await service.register(schema)
        return user
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.post("/login", response_model=Token)
async def login(
    schema: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    try:
        access_token, refresh_token = await service.login(schema.email, schema.password)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    except UnauthorizedException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


@router.post("/refresh", response_model=Token)
async def refresh(
    schema: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    try:
        access_token, refresh_token = await service.refresh_tokens(schema.refresh_token)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    except UnauthorizedException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user
