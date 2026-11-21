import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.payments.models import LedgerEntryType, WalletOwnerType


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_type: WalletOwnerType
    owner_id: uuid.UUID
    currency: str
    available_balance: Decimal
    reserved_balance: Decimal
    created_at: datetime
    updated_at: datetime


class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    reference: str = Field("Deposit funds", min_length=1, max_length=255)


class WithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    reference: str = Field("Withdraw funds", min_length=1, max_length=255)


class LedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    wallet_id: uuid.UUID
    task_id: uuid.UUID | None
    entry_type: LedgerEntryType
    amount: Decimal
    balance_after: Decimal
    reference: str
    created_at: datetime
