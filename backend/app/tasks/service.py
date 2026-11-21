import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.common.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.moderation.schemas import TaskModerationInput
from app.moderation.service import TaskKinModerationService
from app.organizations.models import OrganizationMember
from app.payments.models import WalletOwnerType
from app.payments.service import WalletService
from app.pricing.schemas import PricingInput
from app.pricing.service import TaskKinPricingService
from app.tasks.models import Task, TaskCategory, TaskStatus
from app.tasks.schemas import (
    TaskCreate,
    TaskResponse,
    TaskResponseModeration,
    TaskResponsePricing,
    TaskUpdate,
)
from app.tasks.state_machine import validate_task_transition
from app.webhooks.service import WebhookService


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_service = TaskKinPricingService()
        self.moderation_service = TaskKinModerationService()

    async def _verify_user_membership(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
        res = await self.db.execute(stmt)
        if not res.scalar_one_or_none():
            raise ForbiddenException("User is not a member of the organization")

    async def _calculate_pricing_and_moderation(
        self, task_data: TaskCreate | TaskUpdate, deadline_at: datetime
    ) -> tuple[TaskResponsePricing, TaskResponseModeration]:
        # Calculate hours to deadline
        time_diff = deadline_at - datetime.now(UTC)
        hours_to_deadline = max(0.0, time_diff.total_seconds() / 3600.0)

        # Estimate price
        pricing_in = PricingInput(
            estimated_minutes=task_data.estimated_minutes or 60,
            complexity="normal",  # Can expand in the future
            hours_to_deadline=hours_to_deadline,
            displacement_cost=Decimal("0.00"),
        )
        pricing_res = await self.pricing_service.calculate(pricing_in)

        # Moderation
        mod_in = TaskModerationInput(
            title=task_data.title or "",
            description=task_data.description or "",
            category=task_data.category.value
            if task_data.category
            else "custom_safe_task",
            evidence_requirements=task_data.evidence_requirements or [],
            country=task_data.country,
            city=task_data.city,
            location_mode=task_data.location_mode.value
            if task_data.location_mode
            else "remote",
        )
        mod_res = await self.moderation_service.evaluate_task(mod_in)

        pricing_info = TaskResponsePricing(
            recommended_price=pricing_res.recommended_price,
            minimum_price=pricing_res.minimum_price,
        )

        moderation_info = TaskResponseModeration(
            decision=mod_res.decision,
            risk_level=mod_res.risk_level,
        )

        return pricing_info, moderation_info

    async def create_task(self, schema: TaskCreate, creator_user: User) -> TaskResponse:
        await self._verify_user_membership(schema.organization_id, creator_user.id)

        # Check deadline is in the future
        if schema.deadline_at <= datetime.now(UTC):
            raise BadRequestException("Deadline must be in the future")

        pricing_info, moderation_info = await self._calculate_pricing_and_moderation(
            schema, schema.deadline_at
        )

        # Offered price defaults to recommended price
        offered_price = pricing_info.recommended_price

        task = Task(
            organization_id=schema.organization_id,
            created_by_user_id=creator_user.id,
            title=schema.title,
            description=schema.description,
            category=schema.category,
            status=TaskStatus.DRAFT,
            currency=schema.currency,
            offered_price=offered_price,
            maximum_budget=schema.maximum_budget,
            estimated_minutes=schema.estimated_minutes,
            deadline_at=schema.deadline_at,
            location_mode=schema.location_mode,
            country=schema.country,
            city=schema.city,
            required_skills=schema.required_skills,
            required_languages=schema.required_languages,
            evidence_requirements=schema.evidence_requirements,
            safety_risk_level=moderation_info.risk_level,
            moderation_status=moderation_info.decision,
        )
        self.db.add(task)
        await self.db.flush()

        response = TaskResponse.model_validate(task)
        response.pricing = pricing_info
        response.moderation = moderation_info
        return response

    async def get_task_by_id(self, task_id: uuid.UUID) -> TaskResponse:
        stmt = select(Task).where(Task.id == task_id)
        res = await self.db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise NotFoundException("Task not found")

        response = TaskResponse.model_validate(task)

        # Add current estimates
        pricing_info, moderation_info = await self._calculate_pricing_and_moderation(
            TaskCreate(
                organization_id=task.organization_id,
                title=task.title,
                description=task.description,
                category=task.category,
                estimated_minutes=task.estimated_minutes,
                maximum_budget=task.maximum_budget,
                currency=task.currency,
                deadline_at=task.deadline_at,
                location_mode=task.location_mode,
                country=task.country,
                city=task.city,
                required_skills=task.required_skills,
                required_languages=task.required_languages,
                evidence_requirements=task.evidence_requirements,
            ),
            task.deadline_at,
        )
        response.pricing = pricing_info
        response.moderation = moderation_info
        return response

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        category: TaskCategory | None = None,
        country: str | None = None,
        city: str | None = None,
        minimum_price: Decimal | None = None,
        maximum_price: Decimal | None = None,
        required_skill: str | None = None,
        deadline_before: datetime | None = None,
    ) -> list[Task]:
        stmt = select(Task)
        if status:
            stmt = stmt.where(Task.status == status)
        if category:
            stmt = stmt.where(Task.category == category)
        if country:
            stmt = stmt.where(Task.country == country)
        if city:
            stmt = stmt.where(Task.city == city)
        if minimum_price:
            stmt = stmt.where(Task.offered_price >= minimum_price)
        if maximum_price:
            stmt = stmt.where(Task.offered_price <= maximum_price)
        if deadline_before:
            stmt = stmt.where(Task.deadline_at <= deadline_before)

        res = await self.db.execute(stmt)
        tasks = list(res.scalars().all())

        # If required_skill is provided, filter programmatically since it's stored in JSONB
        if required_skill:
            tasks = [t for t in tasks if required_skill in t.required_skills]

        return tasks

    async def update_task(
        self, task_id: uuid.UUID, schema: TaskUpdate, user: User
    ) -> TaskResponse:
        stmt = select(Task).where(Task.id == task_id)
        res = await self.db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise NotFoundException("Task not found")

        await self._verify_user_membership(task.organization_id, user.id)

        if task.status != TaskStatus.DRAFT:
            raise ConflictException("Only tasks in draft status can be modified")

        # Update fields if provided
        if schema.title is not None:
            task.title = schema.title
        if schema.description is not None:
            task.description = schema.description
        if schema.category is not None:
            task.category = schema.category
        if schema.estimated_minutes is not None:
            task.estimated_minutes = schema.estimated_minutes
        if schema.maximum_budget is not None:
            task.maximum_budget = schema.maximum_budget
        if schema.currency is not None:
            task.currency = schema.currency
        if schema.deadline_at is not None:
            if schema.deadline_at <= datetime.now(UTC):
                raise BadRequestException("Deadline must be in the future")
            task.deadline_at = schema.deadline_at
        if schema.location_mode is not None:
            task.location_mode = schema.location_mode
        if schema.country is not None:
            task.country = schema.country
        if schema.city is not None:
            task.city = schema.city
        if schema.required_skills is not None:
            task.required_skills = schema.required_skills
        if schema.required_languages is not None:
            task.required_languages = schema.required_languages
        if schema.evidence_requirements is not None:
            task.evidence_requirements = schema.evidence_requirements

        # Recompute pricing and moderation
        pricing_info, moderation_info = await self._calculate_pricing_and_moderation(
            TaskCreate(
                organization_id=task.organization_id,
                title=task.title,
                description=task.description,
                category=task.category,
                estimated_minutes=task.estimated_minutes,
                maximum_budget=task.maximum_budget,
                currency=task.currency,
                deadline_at=task.deadline_at,
                location_mode=task.location_mode,
                country=task.country,
                city=task.city,
                required_skills=task.required_skills,
                required_languages=task.required_languages,
                evidence_requirements=task.evidence_requirements,
            ),
            task.deadline_at,
        )

        task.offered_price = pricing_info.recommended_price
        task.safety_risk_level = moderation_info.risk_level
        task.moderation_status = moderation_info.decision

        await self.db.flush()

        response = TaskResponse.model_validate(task)
        response.pricing = pricing_info
        response.moderation = moderation_info
        return response

    async def publish_task(self, task_id: uuid.UUID, user: User) -> TaskResponse:
        stmt = select(Task).where(Task.id == task_id)
        res = await self.db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise NotFoundException("Task not found")

        await self._verify_user_membership(task.organization_id, user.id)

        # Transition logic based on moderation
        if task.moderation_status == "allow":
            # Sequentially validate draft -> pending_moderation -> open
            validate_task_transition(task.status, TaskStatus.PENDING_MODERATION)
            validate_task_transition(TaskStatus.PENDING_MODERATION, TaskStatus.OPEN)
            target_status = TaskStatus.OPEN
        elif task.moderation_status == "manual_review":
            validate_task_transition(task.status, TaskStatus.PENDING_MODERATION)
            target_status = TaskStatus.PENDING_MODERATION
        else:
            raise ConflictException("Cannot publish a rejected task")

        # Reserve funds in organization wallet
        wallet_service = WalletService(self.db)
        org_wallet = await wallet_service.get_wallet_by_owner(
            owner_type=WalletOwnerType.ORGANIZATION, owner_id=task.organization_id
        )
        await wallet_service.reserve_funds(
            wallet_id=org_wallet.id,
            amount=task.offered_price,
            task_id=task.id,
            reference=f"Reserved funds for task {task.id} publication",
        )

        task.status = target_status
        if target_status == TaskStatus.OPEN:
            task.published_at = datetime.now(UTC)

        await self.db.flush()

        try:
            webhook_service = WebhookService(self.db)
            await webhook_service.trigger_event(
                org_id=task.organization_id,
                event_type="task.status_changed",
                payload={"task_id": str(task.id), "status": task.status.value},
            )
        except Exception:
            pass

        return await self.get_task_by_id(task.id)

    async def cancel_task(self, task_id: uuid.UUID, user: User) -> TaskResponse:
        stmt = select(Task).where(Task.id == task_id)
        res = await self.db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise NotFoundException("Task not found")

        await self._verify_user_membership(task.organization_id, user.id)

        validate_task_transition(task.status, TaskStatus.CANCELLED)

        # Refund reserved funds back to available balance
        if task.status in (
            TaskStatus.OPEN,
            TaskStatus.ASSIGNED,
            TaskStatus.SUBMITTED,
            TaskStatus.PENDING_MODERATION,
        ):
            wallet_service = WalletService(self.db)
            org_wallet = await wallet_service.get_wallet_by_owner(
                owner_type=WalletOwnerType.ORGANIZATION, owner_id=task.organization_id
            )
            await wallet_service.refund_funds(
                wallet_id=org_wallet.id,
                amount=task.offered_price,
                task_id=task.id,
                reference=f"Refunded reserved funds for task {task.id} cancellation",
            )

        task.status = TaskStatus.CANCELLED
        await self.db.flush()

        try:
            webhook_service = WebhookService(self.db)
            await webhook_service.trigger_event(
                org_id=task.organization_id,
                event_type="task.status_changed",
                payload={"task_id": str(task.id), "status": task.status.value},
            )
        except Exception:
            pass

        return await self.get_task_by_id(task.id)
