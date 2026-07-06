import re

from fastapi import APIRouter, HTTPException, Query

from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.models.finance import DashboardAnalyzeRequest
from app.services.home_dashboard_service import build_home_dashboard


router = APIRouter(prefix="/api/v1/home", tags=["home"])


def _validate_period(period: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}", period):
        raise HTTPException(status_code=422, detail="period 格式必须为 YYYY-MM")


@router.get("/dashboard")
def get_home_dashboard(period: str = Query(default="2026-06")):
    _validate_period(period)
    try:
        return build_home_dashboard(period, SAMPLE_FINANCE_DATA)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/analyze")
def analyze_home_dashboard(request: DashboardAnalyzeRequest):
    _validate_period(request.period)
    try:
        return build_home_dashboard(request.period, request.records)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
