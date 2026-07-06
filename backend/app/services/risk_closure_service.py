from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.models.finance import RiskItem
from app.models.risk_closure import (
    RiskAssignRequest,
    RiskClosureItem,
    RiskClosureListResponse,
    RiskClosureStatus,
    RiskProcessRecord,
    RiskProcessRecordRequest,
    RiskReviewRecord,
    RiskReviewRecordRequest,
)
from app.services.risk_service import detect_risks


_risk_closures: dict[str, RiskClosureItem] = {}


def reset_risk_closure_store() -> None:
    _risk_closures.clear()


def list_risk_closures(
    period: str,
    status: RiskClosureStatus | None = None,
) -> RiskClosureListResponse:
    items = [_build_closure_item(period, risk) for risk in detect_risks(period, SAMPLE_FINANCE_DATA)]
    open_count = sum(1 for item in items if item.status != "closed")
    closed_count = sum(1 for item in items if item.status == "closed")
    filtered_items = [item for item in items if status is None or item.status == status]
    return RiskClosureListResponse(
        period=period,
        total=len(items),
        open_count=open_count,
        closed_count=closed_count,
        items=filtered_items,
    )


def assign_risk_owner(risk_id: str, request: RiskAssignRequest) -> RiskClosureItem:
    item = _get_existing_or_open_item(request.period, risk_id)
    record_note = request.note or f"分派给 {request.owner}"
    updated = item.model_copy(
        update={
            "status": "assigned",
            "owner": request.owner,
            "due_date": request.due_date,
            "process_records": [
                *item.process_records,
                RiskProcessRecord(
                    id=_new_id("process"),
                    handler=request.owner,
                    action="assign",
                    note=record_note,
                    created_at=_now(),
                ),
            ],
        }
    )
    _risk_closures[_closure_key(request.period, risk_id)] = updated
    return updated


def add_process_record(risk_id: str, request: RiskProcessRecordRequest) -> RiskClosureItem:
    item = _get_existing_or_open_item(request.period, risk_id)
    updated = item.model_copy(
        update={
            "status": request.next_status,
            "process_records": [
                *item.process_records,
                RiskProcessRecord(
                    id=_new_id("process"),
                    handler=request.handler,
                    action=request.action,
                    note=request.note,
                    created_at=_now(),
                ),
            ],
        }
    )
    _risk_closures[_closure_key(request.period, risk_id)] = updated
    return updated


def add_review_record(risk_id: str, request: RiskReviewRecordRequest) -> RiskClosureItem:
    item = _get_existing_or_open_item(request.period, risk_id)
    updated = item.model_copy(
        update={
            "status": request.next_status,
            "review_records": [
                *item.review_records,
                RiskReviewRecord(
                    id=_new_id("review"),
                    reviewer=request.reviewer,
                    conclusion=request.conclusion,
                    created_at=_now(),
                ),
            ],
        }
    )
    _risk_closures[_closure_key(request.period, risk_id)] = updated
    return updated


def _get_existing_or_open_item(period: str, risk_id: str) -> RiskClosureItem:
    risk = _find_detected_risk(period, risk_id)
    return _risk_closures.get(_closure_key(period, risk_id), _open_item(period, risk))


def _build_closure_item(period: str, risk: RiskItem) -> RiskClosureItem:
    return _risk_closures.get(_closure_key(period, risk.id), _open_item(period, risk))


def _open_item(period: str, risk: RiskItem) -> RiskClosureItem:
    return RiskClosureItem(period=period, risk=risk, status="open")


def _find_detected_risk(period: str, risk_id: str) -> RiskItem:
    try:
        risks = detect_risks(period, SAMPLE_FINANCE_DATA)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    risk = next((item for item in risks if item.id == risk_id), None)
    if risk is None:
        raise HTTPException(status_code=404, detail="风险不存在")
    return risk


def _closure_key(period: str, risk_id: str) -> str:
    return f"{period}:{risk_id}"


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
