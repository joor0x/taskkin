from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from app.pricing.schemas import PricingExplanation, PricingInput, PricingResult


class PricingService(Protocol):
    async def calculate(
        self,
        pricing_input: PricingInput,
    ) -> PricingResult: ...


class TaskKinPricingService:
    async def calculate(
        self,
        pricing_input: PricingInput,
    ) -> PricingResult:
        # Base settings
        base_rate = Decimal("15.00")  # 15 EUR/hour
        min_price = Decimal("3.00")  # Min price per task
        platform_fee_pct = Decimal("0.15")  # 15%

        # Complexity multiplier
        complexity_lower = pricing_input.complexity.lower()
        if complexity_lower == "skilled":
            skill_mult = Decimal("1.25")
        elif complexity_lower == "expert":
            skill_mult = Decimal("1.75")
        else:
            skill_mult = Decimal("1.00")

        # Urgency multiplier
        hours = pricing_input.hours_to_deadline
        if hours > 48:
            urgency_mult = Decimal("1.00")
        elif hours > 12:
            urgency_mult = Decimal("1.15")
        elif hours > 2:
            urgency_mult = Decimal("1.35")
        else:
            urgency_mult = Decimal("1.75")

        # Base cost calculation
        estimated_hours = Decimal(pricing_input.estimated_minutes) / Decimal("60.00")
        base_cost = (estimated_hours * base_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Recommended price
        recommended_price = (
            base_cost * skill_mult * urgency_mult + pricing_input.displacement_cost
        )
        if recommended_price < min_price:
            recommended_price = min_price
        recommended_price = recommended_price.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Bounds: minimum is 80% of recommended, maximum is 200% of recommended
        # But minimum cannot be lower than min_price
        minimum_price = (recommended_price * Decimal("0.80")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if minimum_price < min_price:
            minimum_price = min_price

        maximum_price = (recommended_price * Decimal("2.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Fees
        platform_fee = (recommended_price * platform_fee_pct).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        estimated_worker_payment = (recommended_price - platform_fee).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return PricingResult(
            recommended_price=recommended_price,
            minimum_price=minimum_price,
            maximum_price=maximum_price,
            estimated_worker_payment=estimated_worker_payment,
            platform_fee=platform_fee,
            explanation=PricingExplanation(
                base_cost=base_cost,
                urgency_multiplier=urgency_mult,
                skill_multiplier=skill_mult,
            ),
        )
