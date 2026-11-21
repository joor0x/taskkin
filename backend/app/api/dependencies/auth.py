import uuid
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole, UserStatus
from app.common.security import decode_token, hash_api_key
from app.infrastructure.database import get_db
from app.organizations.models import APIKey, Organization, OrganizationMember

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user_or_api_key(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(security_bearer)
    ],
) -> tuple[User | None, Organization | None]:
    """
    Authenticates either a JWT or an API Key.
    Returns (User, Organization).
    If authenticated via JWT, returns (User, None).
    If authenticated via API Key, returns (OwnerUser, Organization).
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials",
        )

    token = credentials.credentials

    # Case 1: API Key
    if token.startswith("tk_live_"):
        hashed_key = hash_api_key(token)
        key_stmt = (
            select(APIKey)
            .where(APIKey.key_hash == hashed_key, APIKey.revoked_at.is_(None))
            .execution_options(populate_existing=True)
        )
        key_res = await db.execute(key_stmt)
        api_key = key_res.scalar_one_or_none()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API Key",
            )

        # Update last used at
        api_key.last_used_at = datetime.now(UTC)
        await db.flush()

        # Fetch Organization and Owner
        org_stmt = select(Organization).where(
            Organization.id == api_key.organization_id
        )
        org_res = await db.execute(org_stmt)
        organization = org_res.scalar_one_or_none()

        if not organization or organization.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Organization is inactive or suspended",
            )

        # Fetch owner user
        owner_stmt = select(User).where(User.id == organization.owner_user_id)
        owner_res = await db.execute(owner_stmt)
        owner = owner_res.scalar_one_or_none()

        if not owner or owner.status == UserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Organization owner account is suspended",
            )

        return owner, organization

    # Case 2: JWT
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
        user_id = uuid.UUID(user_id_str)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    # Fetch user
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is suspended",
        )

    return user, None


async def get_current_user(
    auth_data: Annotated[
        tuple[User | None, Organization | None], Depends(get_current_user_or_api_key)
    ],
) -> User:
    user, _ = auth_data
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return user


# Convenience dependencies
require_admin = RoleChecker([UserRole.ADMIN])
require_requester = RoleChecker([UserRole.REQUESTER, UserRole.ADMIN])
require_worker = RoleChecker([UserRole.WORKER, UserRole.ADMIN])


async def verify_organization_access(
    organization_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_data: Annotated[
        tuple[User, Organization | None], Depends(get_current_user_or_api_key)
    ],
) -> Organization:
    user, api_org = auth_data

    # If API Key was used, verify it matches the organization_id
    if api_org:
        if api_org.id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key is not authorized for this organization",
            )
        return api_org

    # If JWT was used, check organization membership
    if user.role == UserRole.ADMIN:
        # Admins can access any organization
        stmt = select(Organization).where(Organization.id == organization_id)
        res = await db.execute(stmt)
        org = res.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        return org

    member_stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == user.id,
    )
    member_res = await db.execute(member_stmt)
    membership = member_res.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    org_stmt = select(Organization).where(Organization.id == organization_id)
    org_res = await db.execute(org_stmt)
    return org_res.scalar_one()
