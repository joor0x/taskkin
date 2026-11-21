import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.common.exceptions import (
    NotFoundException,
)
from app.common.security import generate_api_key_pair
from app.organizations.models import (
    APIKey,
    Organization,
    OrganizationMember,
    OrganizationRole,
    OrganizationStatus,
)
from app.payments.models import Wallet, WalletOwnerType


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_organization(self, name: str, owner_user: User) -> Organization:
        # Create organization
        org = Organization(
            name=name,
            owner_user_id=owner_user.id,
            status=OrganizationStatus.ACTIVE,
        )
        self.db.add(org)
        await self.db.flush()

        # Add owner to members
        member = OrganizationMember(
            organization_id=org.id,
            user_id=owner_user.id,
            role=OrganizationRole.OWNER,
        )
        self.db.add(member)

        # Create wallet for the organization
        wallet = Wallet(
            owner_type=WalletOwnerType.ORGANIZATION,
            owner_id=org.id,
            currency="EUR",
        )
        self.db.add(wallet)

        await self.db.flush()
        return org

    async def get_organization_by_id(self, org_id: uuid.UUID) -> Organization:
        stmt = select(Organization).where(Organization.id == org_id)
        res = await self.db.execute(stmt)
        org = res.scalar_one_or_none()
        if not org:
            raise NotFoundException("Organization not found")
        return org

    async def list_user_organizations(self, user: User) -> list[Organization]:
        # Fetch organizations where user is a member
        stmt = (
            select(Organization)
            .join(OrganizationMember)
            .where(OrganizationMember.user_id == user.id)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create_api_key(self, org_id: uuid.UUID, name: str) -> tuple[APIKey, str]:
        # Generate API key pair
        raw_key, prefix, hashed_key = generate_api_key_pair()

        api_key = APIKey(
            organization_id=org_id,
            name=name,
            key_hash=hashed_key,
            key_prefix=prefix,
        )
        self.db.add(api_key)
        await self.db.flush()

        return api_key, raw_key

    async def list_api_keys(self, org_id: uuid.UUID) -> list[APIKey]:
        stmt = select(APIKey).where(
            APIKey.organization_id == org_id, APIKey.revoked_at.is_(None)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def revoke_api_key(self, org_id: uuid.UUID, key_id: uuid.UUID) -> None:
        stmt = select(APIKey).where(
            APIKey.id == key_id, APIKey.organization_id == org_id
        )
        res = await self.db.execute(stmt)
        api_key = res.scalar_one_or_none()

        if not api_key:
            raise NotFoundException(
                "API Key not found or does not belong to this organization"
            )

        api_key.revoked_at = datetime.now(UTC)
        await self.db.flush()
