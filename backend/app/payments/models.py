import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class WalletOwnerType(str, enum.Enum):
    ORGANIZATION = "organization"
    WORKER = "worker"


class LedgerEntryType(str, enum.Enum):
    DEPOSIT = "deposit"
    RESERVE = "reserve"
    RELEASE = "release"
    REFUND = "refund"
    PAYMENT = "payment"
    PLATFORM_FEE = "platform_fee"
    ADJUSTMENT = "adjustment"


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_type: Mapped[WalletOwnerType] = mapped_column(SQLEnum(WalletOwnerType))
    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    available_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.00")
    )
    reserved_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.00")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    ledger_entries = relationship(
        "LedgerEntry", back_populates="wallet", cascade="all, delete-orphan"
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(SQLEnum(LedgerEntryType))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    reference: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    wallet = relationship("Wallet", back_populates="ledger_entries")
