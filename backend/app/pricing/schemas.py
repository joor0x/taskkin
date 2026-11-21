from decimal import Decimal

from pydantic import BaseModel, Field


class PricingInput(BaseModel):
    estimated_minutes: int = Field(..., ge=1)
    complexity: str = Field("normal")  # normal, skilled, expert
    hours_to_deadline: float = Field(..., ge=0)
    displacement_cost: Decimal = Field(Decimal("0.00"), ge=0)


class PricingExplanation(BaseModel):
    base_cost: Decimal
    urgency_multiplier: Decimal
    skill_multiplier: Decimal


class PricingResult(BaseModel):
    recommended_price: Decimal
    minimum_price: Decimal
    maximum_price: Decimal
    estimated_worker_payment: Decimal
    platform_fee: Decimal
    explanation: PricingExplanation
