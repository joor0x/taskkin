import uuid
from datetime import UTC, datetime

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User, UserRole, UserStatus
from app.auth.schemas import UserRegister
from app.common.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.common.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.payments.models import Wallet, WalletOwnerType
from app.workers.models import WorkerProfile


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, schema: UserRegister) -> User:
        # Check if user already exists
        stmt = select(User).where(User.email == schema.email)
        res = await self.db.execute(stmt)
        if res.scalar_one_or_none():
            raise ConflictException("Email is already registered")

        # Create user
        user = User(
            email=schema.email,
            password_hash=hash_password(schema.password),
            role=schema.role,
            status=UserStatus.ACTIVE,
        )
        self.db.add(user)
        await self.db.flush()

        # If user is a worker, create a worker profile
        if schema.role == UserRole.WORKER:
            profile = WorkerProfile(
                user_id=user.id,
                display_name=schema.email.split("@")[0],  # Default display name
            )
            self.db.add(profile)
            await self.db.flush()

            # Create wallet for the worker
            wallet = Wallet(
                owner_type=WalletOwnerType.WORKER,
                owner_id=profile.id,
                currency="EUR",
            )
            self.db.add(wallet)
            await self.db.flush()

        return user

    async def login(self, email: str, password: str) -> tuple[str, str]:
        stmt = select(User).where(User.email == email)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Incorrect email or password")

        if user.status == UserStatus.SUSPENDED:
            raise UnauthorizedException("Your account is suspended")

        # Generate tokens
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        # Decode refresh token expiration
        decoded = decode_token(refresh_token)
        exp = datetime.fromtimestamp(decoded["exp"], tz=UTC)

        # Store refresh token in DB
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=exp,
        )
        self.db.add(db_refresh_token)
        await self.db.flush()

        return access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Invalid token type")
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise UnauthorizedException("Invalid token payload")
            user_id = uuid.UUID(user_id_str)
        except jwt.PyJWTError:
            raise UnauthorizedException("Invalid or expired refresh token")

        # Check DB for refresh token and verify it is not revoked
        stmt = select(RefreshToken).where(
            RefreshToken.token == refresh_token, RefreshToken.revoked_at.is_(None)
        )
        res = await self.db.execute(stmt)
        db_token = res.scalar_one_or_none()

        if not db_token or db_token.expires_at < datetime.now(UTC):
            raise UnauthorizedException("Refresh token is expired or revoked")

        # Check user status
        user_stmt = select(User).where(User.id == user_id)
        user_res = await self.db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user or user.status == UserStatus.SUSPENDED:
            raise UnauthorizedException("User account is inactive or suspended")

        # Revoke old refresh token (rotate tokens)
        db_token.revoked_at = datetime.now(UTC)

        # Generate new pair
        new_access_token = create_access_token(subject=user.id)
        new_refresh_token = create_refresh_token(subject=user.id)
        new_decoded = decode_token(new_refresh_token)
        new_exp = datetime.fromtimestamp(new_decoded["exp"], tz=UTC)

        # Store new refresh token
        new_db_token = RefreshToken(
            user_id=user.id,
            token=new_refresh_token,
            expires_at=new_exp,
        )
        self.db.add(new_db_token)
        await self.db.flush()

        return new_access_token, new_refresh_token

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        user_stmt = select(User).where(User.id == user_id)
        user_res = await self.db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            raise NotFoundException("User not found")
        return user
