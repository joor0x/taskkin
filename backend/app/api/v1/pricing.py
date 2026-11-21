from fastapi import APIRouter

from app.pricing.schemas import PricingInput, PricingResult
from app.pricing.service import TaskKinPricingService

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/estimate", response_model=PricingResult)
async def estimate_price(
    schema: PricingInput,
):
    service = TaskKinPricingService()
    result = await service.calculate(schema)
    return result
