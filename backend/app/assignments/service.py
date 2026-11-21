import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assignments.models import AssignmentStatus, TaskAssignment
from app.auth.models import User
from app.common.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.tasks.models import Task, TaskStatus
from app.tasks.state_machine import validate_task_transition
from app.workers.models import WorkerProfile


class AssignmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def claim_task(self, task_id: uuid.UUID, worker_user: User) -> TaskAssignment:
        # Fetch worker profile
        profile_stmt = select(WorkerProfile).where(
            WorkerProfile.user_id == worker_user.id
        )
        profile_res = await self.db.execute(profile_stmt)
        worker_profile = profile_res.scalar_one_or_none()
        if not worker_profile:
            raise ForbiddenException("User does not have a worker profile")

        # Fetch task
        task_stmt = select(Task).where(Task.id == task_id)
        task_res = await self.db.execute(task_stmt)
        task = task_res.scalar_one_or_none()
        if not task:
            raise NotFoundException("Task not found")

        # Validate task status
        if task.status != TaskStatus.OPEN:
            raise ConflictException(
                f"Task is in '{task.status.value}' state and cannot be claimed"
            )

        # Check deadline
        if task.deadline_at <= datetime.now(UTC):
            task.status = TaskStatus.EXPIRED
            await self.db.flush()
            raise ConflictException("Task has already expired")

        # Transition task to ASSIGNED
        validate_task_transition(task.status, TaskStatus.ASSIGNED)
        task.status = TaskStatus.ASSIGNED

        # Create assignment
        assignment = TaskAssignment(
            task_id=task.id,
            worker_id=worker_profile.id,
            status=AssignmentStatus.ACTIVE,
            accepted_at=datetime.now(UTC),
        )
        self.db.add(assignment)
        await self.db.flush()

        try:
            from app.webhooks.service import WebhookService

            webhook_service = WebhookService(self.db)
            await webhook_service.trigger_event(
                org_id=task.organization_id,
                event_type="task.status_changed",
                payload={"task_id": str(task.id), "status": task.status.value},
            )
        except Exception:
            pass

        return assignment

    async def get_assignment_by_id(self, assignment_id: uuid.UUID) -> TaskAssignment:
        stmt = select(TaskAssignment).where(TaskAssignment.id == assignment_id)
        res = await self.db.execute(stmt)
        assignment = res.scalar_one_or_none()
        if not assignment:
            raise NotFoundException("Assignment not found")
        return assignment

    async def cancel_assignment(
        self, assignment_id: uuid.UUID, user: User
    ) -> TaskAssignment:
        assignment = await self.get_assignment_by_id(assignment_id)

        # Check permission: must be the worker assigned, or owner/member of the task's organization
        # Fetch task
        task_stmt = select(Task).where(Task.id == assignment.task_id)
        task_res = await self.db.execute(task_stmt)
        task = task_res.scalar_one()

        is_worker = False
        profile_stmt = select(WorkerProfile).where(WorkerProfile.user_id == user.id)
        profile_res = await self.db.execute(profile_stmt)
        worker_profile = profile_res.scalar_one_or_none()
        if worker_profile and worker_profile.id == assignment.worker_id:
            is_worker = True

        if not is_worker:
            # Check if user is task creator/org member (for now, allow if they created it, or admin)
            if task.created_by_user_id != user.id and user.role != "admin":
                raise ForbiddenException(
                    "You do not have permission to cancel this assignment"
                )

        if assignment.status not in (
            AssignmentStatus.ACTIVE,
            AssignmentStatus.SUBMITTED,
        ):
            raise ConflictException(
                f"Cannot cancel assignment in '{assignment.status.value}' state"
            )

        # Update assignment status
        assignment.status = AssignmentStatus.CANCELLED
        assignment.cancelled_at = datetime.now(UTC)

        # Release task back to OPEN so other workers can claim it (unless it has expired)
        if task.deadline_at > datetime.now(UTC):
            task.status = TaskStatus.OPEN
        else:
            task.status = TaskStatus.EXPIRED

        # Record reputation event if worker cancelled
        if is_worker:
            from app.reputation.models import ReputationEventType
            from app.reputation.service import ReputationService

            rep_service = ReputationService(self.db)
            await rep_service.record_event(
                user_id=user.id,
                task_id=task.id,
                event_type=ReputationEventType.WORKER_CANCELLED,
                score=0.0,
                weight=1.0,
            )

        await self.db.flush()

        try:
            from app.webhooks.service import WebhookService

            webhook_service = WebhookService(self.db)
            await webhook_service.trigger_event(
                org_id=task.organization_id,
                event_type="task.status_changed",
                payload={"task_id": str(task.id), "status": task.status.value},
            )
        except Exception:
            pass

        return assignment
