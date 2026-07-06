from fastapi import APIRouter

from app.models.ecommerce import ECommerceProfitRequest
from app.services.ecommerce_profit_service import analyze_ecommerce_profit


router = APIRouter(prefix="/api/v1/ecommerce", tags=["ecommerce"])


@router.post("/profit/analyze")
def analyze_profit(request: ECommerceProfitRequest):
    return analyze_ecommerce_profit(request)
