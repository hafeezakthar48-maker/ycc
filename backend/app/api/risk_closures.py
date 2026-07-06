from fastapi import APIRouter

from app.models.risk_closure import (
    RiskAssignRequest,
    RiskClosureItem,
    RiskClosureListResponse,
    RiskClosureStatus,
    RiskProcessRecordRequest,
    RiskReviewRecordRequest,
)
from app.services.risk_closure_service import (
    add_process_record,
    add_review_record,
    assign_risk_owner,
    list_risk_closures,
)


router = APIRouter(prefix="/api/v1/risks/closures", tags=["risk-closures"])


@router.get("", response_model=RiskClosureListResponse)
def get_risk_closures(period: str = "2026-06", status: RiskClosureStatus | None = None):
    return list_risk_closures(period=period, status=status)


@router.post("/{risk_id}/assign", response_model=RiskClosureItem)
def assign_risk(risk_id: str, request: RiskAssignRequest):
    return assign_risk_owner(risk_id, request)


@router.post("/{risk_id}/process-records", response_model=RiskClosureItem)
def create_process_record(risk_id: str, request: RiskProcessRecordRequest):
    return add_process_record(risk_id, request)


@router.post("/{risk_id}/review-records", response_model=RiskClosureItem)
def create_review_record(risk_id: str, request: RiskReviewRecordRequest):
    return add_review_record(risk_id, request)
