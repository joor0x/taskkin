import asyncio
import threading
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.assignments.models import AssignmentStatus, TaskAssignment
from app.infrastructure.celery import celery_app
from app.infrastructure.database import async_session_factory
from app.payments.models import LedgerEntry, LedgerEntryType, Wallet, WalletOwnerType
from app.tasks.models import Task, TaskStatus


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        result = []

        def target():
            new_loop = asyncio.new_event_loop()
            try:
                result.append(new_loop.run_until_complete(coro))
            finally:
                new_loop.close()

        t = threading.Thread(target=target)
        t.start()
        t.join()
        return result[0]
    else:
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()


@celery_app.task
def check_expired_tasks():
    """Periodic task to expire tasks and assignments that have passed their deadline."""

    async def _run():
        async with async_session_factory() as db:
            now = datetime.now(UTC)

            # 1. Fetch expired OPEN tasks
            open_stmt = select(Task).where(
                Task.status == TaskStatus.OPEN, Task.deadline_at <= now
            )
            open_res = await db.execute(open_stmt)
            expired_open_tasks = open_res.scalars().all()

            for task in expired_open_tasks:
                task.status = TaskStatus.EXPIRED
                # Refund escrow (since it was open, funds were reserved)
                wallet_stmt = select(Wallet).where(
                    Wallet.owner_type == WalletOwnerType.ORGANIZATION,
                    Wallet.owner_id == task.organization_id,
                )
                wallet_res = await db.execute(wallet_stmt)
                wallet = wallet_res.scalar_one_or_none()
                if wallet:
                    wallet.reserved_balance = max(
                        Decimal("0.00"), wallet.reserved_balance - task.offered_price
                    )
                    wallet.available_balance += task.offered_price

                    ledger = LedgerEntry(
                        wallet_id=wallet.id,
                        amount=task.offered_price,
                        balance_after=wallet.available_balance,
                        entry_type=LedgerEntryType.REFUND,
                        reference=f"Refunded reserve for task {task.id} expiration",
                    )
                    db.add(ledger)

                try:
                    from app.webhooks.service import WebhookService

                    await WebhookService(db).trigger_event(
                        org_id=task.organization_id,
                        event_type="task.status_changed",
                        payload={"task_id": str(task.id), "status": "expired"},
                    )
                except Exception:
                    pass

            # 2. Fetch expired ASSIGNED tasks
            assigned_stmt = select(Task).where(
                Task.status == TaskStatus.ASSIGNED, Task.deadline_at <= now
            )
            assigned_res = await db.execute(assigned_stmt)
            expired_assigned_tasks = assigned_res.scalars().all()

            for task in expired_assigned_tasks:
                task.status = TaskStatus.EXPIRED

                # Cancel its active assignment
                assign_stmt = select(TaskAssignment).where(
                    TaskAssignment.task_id == task.id,
                    TaskAssignment.status == AssignmentStatus.ACTIVE,
                )
                assign_res = await db.execute(assign_stmt)
                assignment = assign_res.scalar_one_or_none()
                if assignment:
                    assignment.status = AssignmentStatus.CANCELLED
                    assignment.cancelled_at = now

                # Refund organization escrow
                wallet_stmt = select(Wallet).where(
                    Wallet.owner_type == WalletOwnerType.ORGANIZATION,
                    Wallet.owner_id == task.organization_id,
                )
                wallet_res = await db.execute(wallet_stmt)
                wallet = wallet_res.scalar_one_or_none()
                if wallet:
                    wallet.reserved_balance = max(
                        Decimal("0.00"), wallet.reserved_balance - task.offered_price
                    )
                    wallet.available_balance += task.offered_price

                    ledger = LedgerEntry(
                        wallet_id=wallet.id,
                        amount=task.offered_price,
                        balance_after=wallet.available_balance,
                        entry_type=LedgerEntryType.REFUND,
                        reference=f"Refunded reserve for task {task.id} expiration",
                    )
                    db.add(ledger)

                try:
                    from app.webhooks.service import WebhookService

                    await WebhookService(db).trigger_event(
                        org_id=task.organization_id,
                        event_type="task.status_changed",
                        payload={"task_id": str(task.id), "status": "expired"},
                    )
                except Exception:
                    pass

            if expired_open_tasks or expired_assigned_tasks:
                await db.commit()

    run_async(_run())
