import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.reputation.models import ReputationEvent, ReputationEventType


class ReputationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        user_id: uuid.UUID,
        task_id: uuid.UUID | None,
        event_type: ReputationEventType,
        score: float,
        weight: float = 1.0,
        metadata_json: dict | None = None,
    ) -> ReputationEvent:
        event = ReputationEvent(
            user_id=user_id,
            task_id=task_id,
            event_type=event_type,
            score=score,
            weight=weight,
            metadata_json=metadata_json or {},
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def calculate_worker_reputation(self, worker_user_id: uuid.UUID) -> dict:
        stmt = select(ReputationEvent).where(ReputationEvent.user_id == worker_user_id)
        res = await self.db.execute(stmt)
        events = res.scalars().all()

        completed_tasks = 0
        cancelled_tasks = 0
        disputes = 0

        # Sub-scores lists
        quality_ratings = []
        reliability_ratings = []
        on_time_ratings = []
        instruction_ratings = []

        for event in events:
            if event.event_type == ReputationEventType.TASK_APPROVED:
                completed_tasks += 1
                meta = event.metadata_json or {}
                if "quality" in meta:
                    quality_ratings.append(float(meta["quality"]))
                if "reliability" in meta:
                    reliability_ratings.append(float(meta["reliability"]))
                if "on_time" in meta:
                    on_time_ratings.append(float(meta["on_time"]))
                if "instruction" in meta:
                    instruction_ratings.append(float(meta["instruction"]))

            elif event.event_type == ReputationEventType.WORKER_CANCELLED:
                cancelled_tasks += 1
            elif event.event_type == ReputationEventType.DISPUTE_RESOLVED:
                disputes += 1

        # Calculate averages, default to 4.0 if empty
        quality_score = (
            sum(quality_ratings) / len(quality_ratings) if quality_ratings else 4.0
        )
        reliability_score = (
            sum(reliability_ratings) / len(reliability_ratings)
            if reliability_ratings
            else 4.0
        )
        on_time_score = (
            sum(on_time_ratings) / len(on_time_ratings) if on_time_ratings else 4.0
        )
        instruction_score = (
            sum(instruction_ratings) / len(instruction_ratings)
            if instruction_ratings
            else 4.0
        )

        total_tasks = completed_tasks + cancelled_tasks
        dispute_rate = disputes / total_tasks if total_tasks > 0 else 0.0

        # Bayesian Score
        # bayesian_score = (C * m + N * R) / (C + N)
        # Prior constants
        C = 5.0  # Confidence weight (number of reviews)
        m = 4.0  # Prior mean rating

        # Calculate current mean rating (R) of the worker
        # Average of sub-scores
        rating_avg = (
            quality_score + reliability_score + on_time_score + instruction_score
        ) / 4.0

        N = float(completed_tasks)
        bayesian_score = (C * m + N * rating_avg) / (C + N)

        return {
            "quality_score": round(quality_score, 2),
            "reliability_score": round(reliability_score, 2),
            "on_time_score": round(on_time_score, 2),
            "instruction_score": round(instruction_score, 2),
            "dispute_rate": round(dispute_rate, 4),
            "completed_tasks": completed_tasks,
            "cancelled_tasks": cancelled_tasks,
            "bayesian_score": round(bayesian_score, 2),
        }
