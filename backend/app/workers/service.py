import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException
from app.workers.models import WorkerProfile
from app.workers.schemas import WorkerProfileUpdate


class WorkerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_worker_profile_by_user_id(self, user_id: uuid.UUID) -> WorkerProfile:
        stmt = select(WorkerProfile).where(WorkerProfile.user_id == user_id)
        res = await self.db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise NotFoundException("Worker profile not found")
        return profile

    async def update_worker_profile(
        self, user_id: uuid.UUID, schema: WorkerProfileUpdate
    ) -> WorkerProfile:
        profile = await self.get_worker_profile_by_user_id(user_id)

        # Update fields if provided
        if schema.display_name is not None:
            profile.display_name = schema.display_name
        if schema.bio is not None:
            profile.bio = schema.bio
        if schema.country is not None:
            profile.country = schema.country
        if schema.city is not None:
            profile.city = schema.city

        # Round lat/lon to 3 decimal places to enforce approximate location
        if schema.latitude_approx is not None:
            profile.latitude_approx = round(schema.latitude_approx, 3)
        if schema.longitude_approx is not None:
            profile.longitude_approx = round(schema.longitude_approx, 3)

        if schema.languages is not None:
            profile.languages = schema.languages
        if schema.skills is not None:
            profile.skills = schema.skills
        if schema.availability_status is not None:
            profile.availability_status = schema.availability_status

        await self.db.flush()
        return profile
