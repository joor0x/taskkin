import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    ConflictException,
    NotFoundException,
)
from app.payments.models import LedgerEntry, LedgerEntryType, Wallet, WalletOwnerType


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wallet_by_id(self, wallet_id: uuid.UUID) -> Wallet:
        stmt = select(Wallet).where(Wallet.id == wallet_id)
        res = await self.db.execute(stmt)
        wallet = res.scalar_one_or_none()
        if not wallet:
            raise NotFoundException("Wallet not found")
        return wallet

    async def get_wallet_by_owner(
        self, owner_type: WalletOwnerType, owner_id: uuid.UUID
    ) -> Wallet:
        stmt = select(Wallet).where(
            Wallet.owner_type == owner_type, Wallet.owner_id == owner_id
        )
        res = await self.db.execute(stmt)
        wallet = res.scalar_one_or_none()
        if not wallet:
            # Initialize wallet if it doesn't exist for some reason
            wallet = Wallet(
                owner_type=owner_type,
                owner_id=owner_id,
                currency="EUR",
                available_balance=Decimal("0.00"),
                reserved_balance=Decimal("0.00"),
            )
            self.db.add(wallet)
            await self.db.flush()
        return wallet

    async def deposit_funds(
        self, wallet_id: uuid.UUID, amount: Decimal, reference: str
    ) -> Wallet:
        wallet = await self.get_wallet_by_id(wallet_id)
        wallet.available_balance += amount

        ledger = LedgerEntry(
            wallet_id=wallet.id,
            amount=amount,
            balance_after=wallet.available_balance,
            entry_type=LedgerEntryType.DEPOSIT,
            reference=reference,
        )
        self.db.add(ledger)
        await self.db.flush()
        return wallet

    async def withdraw_funds(
        self, wallet_id: uuid.UUID, amount: Decimal, reference: str
    ) -> Wallet:
        wallet = await self.get_wallet_by_id(wallet_id)
        if wallet.available_balance < amount:
            raise ConflictException("Insufficient available funds for withdrawal")

        wallet.available_balance -= amount

        ledger = LedgerEntry(
            wallet_id=wallet.id,
            amount=-amount,
            balance_after=wallet.available_balance,
            entry_type=LedgerEntryType.ADJUSTMENT,
            reference=reference,
        )
        self.db.add(ledger)
        await self.db.flush()
        return wallet

    async def reserve_funds(
        self, wallet_id: uuid.UUID, amount: Decimal, task_id: uuid.UUID, reference: str
    ) -> Wallet:
        wallet = await self.get_wallet_by_id(wallet_id)
        if wallet.available_balance < amount:
            raise ConflictException("Insufficient available balance to reserve funds")

        wallet.available_balance -= amount
        wallet.reserved_balance += amount

        ledger = LedgerEntry(
            wallet_id=wallet.id,
            task_id=task_id,
            amount=-amount,
            balance_after=wallet.available_balance,
            entry_type=LedgerEntryType.RESERVE,
            reference=reference,
        )
        self.db.add(ledger)
        await self.db.flush()
        return wallet

    async def release_funds(
        self, wallet_id: uuid.UUID, amount: Decimal, task_id: uuid.UUID, reference: str
    ) -> Wallet:
        wallet = await self.get_wallet_by_id(wallet_id)
        wallet.reserved_balance = max(Decimal("0.00"), wallet.reserved_balance - amount)

        ledger = LedgerEntry(
            wallet_id=wallet.id,
            task_id=task_id,
            amount=-amount,
            balance_after=wallet.available_balance,
            entry_type=LedgerEntryType.RELEASE,
            reference=reference,
        )
        self.db.add(ledger)
        await self.db.flush()
        return wallet

    async def refund_funds(
        self, wallet_id: uuid.UUID, amount: Decimal, task_id: uuid.UUID, reference: str
    ) -> Wallet:
        wallet = await self.get_wallet_by_id(wallet_id)
        wallet.reserved_balance = max(Decimal("0.00"), wallet.reserved_balance - amount)
        wallet.available_balance += amount

        ledger = LedgerEntry(
            wallet_id=wallet.id,
            task_id=task_id,
            amount=amount,
            balance_after=wallet.available_balance,
            entry_type=LedgerEntryType.REFUND,
            reference=reference,
        )
        self.db.add(ledger)
        await self.db.flush()
        return wallet

    async def get_ledger(self, wallet_id: uuid.UUID) -> list[LedgerEntry]:
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet_id)
            .order_by(LedgerEntry.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
