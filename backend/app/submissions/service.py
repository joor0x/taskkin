import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.assignments.models import AssignmentStatus, TaskAssignment
from app.auth.models import User
from app.common.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.evidence.models import Evidence
from app.organizations.models import OrganizationMember
from app.payments.models import LedgerEntry, LedgerEntryType, Wallet, WalletOwnerType
from app.submissions.models import Submission, SubmissionStatus
from app.submissions.schemas import SubmissionCreate
from app.tasks.models import Task, TaskStatus
from app.tasks.state_machine import validate_task_transition
from app.workers.models import WorkerProfile


class SubmissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_submission(
        self, schema: SubmissionCreate, worker_user: User
    ) -> Submission:
        # Verify worker profile
        profile_stmt = select(WorkerProfile).where(
            WorkerProfile.user_id == worker_user.id
        )
        profile_res = await self.db.execute(profile_stmt)
        worker_profile = profile_res.scalar_one_or_none()
        if not worker_profile:
            raise ForbiddenException("User does not have a worker profile")

        # Fetch assignment
        assignment_stmt = select(TaskAssignment).where(
            TaskAssignment.id == schema.assignment_id,
            TaskAssignment.worker_id == worker_profile.id,
        )
        assignment_res = await self.db.execute(assignment_stmt)
        assignment = assignment_res.scalar_one_or_none()
        if not assignment:
            raise NotFoundException("Active assignment not found for this worker")

        if assignment.status != AssignmentStatus.ACTIVE:
            raise ConflictException(
                f"Cannot submit for assignment in '{assignment.status.value}' state"
            )

        # Fetch task
        task_stmt = select(Task).where(Task.id == assignment.task_id)
        task_res = await self.db.execute(task_stmt)
        task = task_res.scalar_one()

        # Check deadline
        if task.deadline_at <= datetime.now(UTC):
            task.status = TaskStatus.EXPIRED
            assignment.status = AssignmentStatus.CANCELLED
            await self.db.flush()
            raise ConflictException("Task has expired")

        # Transition task to SUBMITTED
        validate_task_transition(task.status, TaskStatus.SUBMITTED)
        task.status = TaskStatus.SUBMITTED

        # Create submission
        submission = Submission(
            assignment_id=assignment.id,
            worker_id=worker_profile.id,
            text_result=schema.text_result,
            structured_result=schema.structured_result,
            status=SubmissionStatus.PENDING,
            submitted_at=datetime.now(UTC),
        )
        self.db.add(submission)
        await self.db.flush()

        # Add evidences
        for ev in schema.evidences:
            evidence = Evidence(
                submission_id=submission.id,
                evidence_type=ev.evidence_type,
                storage_key=ev.storage_key,
                file_name=ev.file_name,
                mime_type=ev.mime_type,
                file_size=ev.file_size,
                sha256=ev.sha256,
                metadata_json=ev.metadata_json,
            )
            self.db.add(evidence)

        # Transition assignment to SUBMITTED
        assignment.status = AssignmentStatus.SUBMITTED
        assignment.submitted_at = datetime.now(UTC)

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

        return submission

    async def get_submission_by_id(self, submission_id: uuid.UUID) -> Submission:
        stmt = (
            select(Submission)
            .options(selectinload(Submission.evidence))
            .where(Submission.id == submission_id)
        )
        res = await self.db.execute(stmt)
        submission = res.scalar_one_or_none()
        if not submission:
            raise NotFoundException("Submission not found")
        return submission

    async def _verify_reviewer_membership(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
        res = await self.db.execute(stmt)
        if not res.scalar_one_or_none():
            raise ForbiddenException(
                "Reviewer is not a member of the task organization"
            )

    async def approve_submission(
        self,
        submission_id: uuid.UUID,
        reviewer: User,
        notes: str | None = None,
        quality_rating: float | None = None,
        reliability_rating: float | None = None,
        on_time_rating: float | None = None,
        instruction_rating: float | None = None,
    ) -> Submission:
        submission = await self.get_submission_by_id(submission_id)
        if submission.status != SubmissionStatus.PENDING:
            raise ConflictException(
                f"Submission is already '{submission.status.value}'"
            )

        # Fetch assignment and task
        assignment_stmt = select(TaskAssignment).where(
            TaskAssignment.id == submission.assignment_id
        )
        assignment_res = await self.db.execute(assignment_stmt)
        assignment = assignment_res.scalar_one()

        task_stmt = select(Task).where(Task.id == assignment.task_id)
        task_res = await self.db.execute(task_stmt)
        task = task_res.scalar_one()

        # Check permissions
        if reviewer.role != "admin":
            await self._verify_reviewer_membership(task.organization_id, reviewer.id)

        # Transition Task status to APPROVED
        validate_task_transition(task.status, TaskStatus.APPROVED)
        task.status = TaskStatus.APPROVED

        # Update submission and assignment
        submission.status = SubmissionStatus.APPROVED
        submission.reviewed_at = datetime.now(UTC)
        submission.review_notes = notes

        assignment.status = AssignmentStatus.COMPLETED
        assignment.completed_at = datetime.now(UTC)

        # Fetch worker user ID to record reputation
        worker_profile_stmt = select(WorkerProfile).where(
            WorkerProfile.id == assignment.worker_id
        )
        worker_profile_res = await self.db.execute(worker_profile_stmt)
        worker_profile = worker_profile_res.scalar_one()
        worker_user_id = worker_profile.user_id

        # Record reputation event
        from app.reputation.models import ReputationEventType
        from app.reputation.service import ReputationService

        rep_service = ReputationService(self.db)
        ratings = {
            "quality": quality_rating if quality_rating is not None else 5.0,
            "reliability": reliability_rating
            if reliability_rating is not None
            else 5.0,
            "on_time": on_time_rating if on_time_rating is not None else 5.0,
            "instruction": instruction_rating
            if instruction_rating is not None
            else 5.0,
        }
        avg_rating = sum(ratings.values()) / 4.0

        await rep_service.record_event(
            user_id=worker_user_id,
            task_id=task.id,
            event_type=ReputationEventType.TASK_APPROVED,
            score=avg_rating,
            weight=1.0,
            metadata_json=ratings,
        )

        # Ledger & Wallet payouts escrow release
        # Platform fee = 15%
        platform_fee = (task.offered_price * Decimal("0.15")).quantize(Decimal("0.01"))
        worker_payout = task.offered_price - platform_fee

        # Organization Wallet
        org_wallet_stmt = select(Wallet).where(
            Wallet.owner_type == WalletOwnerType.ORGANIZATION,
            Wallet.owner_id == task.organization_id,
        )
        org_wallet_res = await self.db.execute(org_wallet_stmt)
        org_wallet = org_wallet_res.scalar_one_or_none()
        if org_wallet:
            # Release escrow
            org_wallet.reserved_balance = max(
                Decimal("0.00"), org_wallet.reserved_balance - task.offered_price
            )

            # Record Ledger Entry
            org_ledger = LedgerEntry(
                wallet_id=org_wallet.id,
                amount=-task.offered_price,
                balance_after=org_wallet.available_balance,
                entry_type=LedgerEntryType.RELEASE,
                reference=f"Released reserve for task {task.id} approval",
            )
            self.db.add(org_ledger)

        # Worker Wallet
        worker_wallet_stmt = select(Wallet).where(
            Wallet.owner_type == WalletOwnerType.WORKER,
            Wallet.owner_id == assignment.worker_id,
        )
        worker_wallet_res = await self.db.execute(worker_wallet_stmt)
        worker_wallet = worker_wallet_res.scalar_one_or_none()
        if worker_wallet:
            worker_wallet.available_balance += worker_payout

            # Record Ledger Entry
            worker_ledger = LedgerEntry(
                wallet_id=worker_wallet.id,
                amount=worker_payout,
                balance_after=worker_wallet.available_balance,
                entry_type=LedgerEntryType.PAYMENT,
                reference=f"Received payment for task {task.id} approval",
            )
            self.db.add(worker_ledger)

        await self.db.flush()

        try:
            from app.webhooks.service import WebhookService

            webhook_service = WebhookService(self.db)

            # 1. task.status_changed
            await webhook_service.trigger_event(
                org_id=task.organization_id,
                event_type="task.status_changed",
                payload={"task_id": str(task.id), "status": task.status.value},
            )

            # 2. payment.completed
            await webhook_service.trigger_event(
                org_id=task.organization_id,
                event_type="payment.completed",
                payload={
                    "task_id": str(task.id),
                    "amount": str(task.offered_price),
                    "platform_fee": str(platform_fee),
                    "worker_payout": str(worker_payout),
                },
            )

            # 3. reputation.updated
            worker_rep = await rep_service.calculate_worker_reputation(worker_user_id)
            await webhook_service.trigger_event(
                org_id=task.organization_id,
                event_type="reputation.updated",
                payload={
                    "worker_user_id": str(worker_user_id),
                    "reputation": worker_rep,
                },
            )
        except Exception:
            pass

        return submission

    async def reject_submission(
        self, submission_id: uuid.UUID, reviewer: User, notes: str | None = None
    ) -> Submission:
        submission = await self.get_submission_by_id(submission_id)
        if submission.status != SubmissionStatus.PENDING:
            raise ConflictException(
                f"Submission is already '{submission.status.value}'"
            )

        # Fetch assignment and task
        assignment_stmt = select(TaskAssignment).where(
            TaskAssignment.id == submission.assignment_id
        )
        assignment_res = await self.db.execute(assignment_stmt)
        assignment = assignment_res.scalar_one()

        task_stmt = select(Task).where(Task.id == assignment.task_id)
        task_res = await self.db.execute(task_stmt)
        task = task_res.scalar_one()

        # Check permissions
        if reviewer.role != "admin":
            await self._verify_reviewer_membership(task.organization_id, reviewer.id)

        # Transition task back to ASSIGNED (so worker can fix it and submit again)
        validate_task_transition(
            task.status, TaskStatus.REJECTED
        )  # Validate transition to rejected state
        validate_task_transition(
            TaskStatus.REJECTED, TaskStatus.ASSIGNED
        )  # Validate re-assigning
        task.status = TaskStatus.ASSIGNED

        # Update submission and assignment
        submission.status = SubmissionStatus.REJECTED
        submission.reviewed_at = datetime.now(UTC)
        submission.review_notes = notes

        # Active assignment goes back to ACTIVE so it can accept a new submission
        assignment.status = AssignmentStatus.ACTIVE
        assignment.submitted_at = None

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

        return submission
