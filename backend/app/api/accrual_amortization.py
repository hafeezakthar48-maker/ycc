from fastapi import APIRouter, Header, HTTPException, Query

from app.models.accrual_amortization import (
    AccountingScheduleCreate,
    AccountingScheduleListResponse,
    LoanInterestPostRequest,
    LoanScheduleCreate,
    SchedulePostRequest,
)
from app.models.system_admin import AuditLogCreateRequest
from app.services.accrual_amortization_service import (
    create_accounting_schedule,
    create_loan_schedule,
    get_loan_schedule,
    list_accounting_schedules,
    list_loan_schedules,
    post_loan_interest_accrual,
    post_schedule_for_period,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/accrual-amortization", tags=["accrual-amortization"])


@router.get("/schedules")
def get_accrual_amortization_schedules(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "accrual_amortization.schedule.read"
    target_id = f"accrual-amortization:{account_set_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="accrual_amortization.read",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id},
    )
    schedules = list_accounting_schedules(account_set_id)
    loans = list_loan_schedules(account_set_id)
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id, "schedule_count": len(schedules), "loan_count": len(loans)},
    )
    return AccountingScheduleListResponse(
        account_set_id=account_set_id,
        total_schedules=len(schedules),
        total_loans=len(loans),
        schedules=schedules,
        loan_schedules=loans,
    )


@router.post("/schedules")
def post_accrual_amortization_schedule(
    request: AccountingScheduleCreate,
    x_actor_id: str = Header(default="system"),
):
    event = "accrual_amortization.schedule.create"
    target_id = f"accrual-amortization-schedule:{request.account_set_id}:{request.schedule_code}"
    metadata = _request_metadata(request)
    _require_permission(x_actor_id, "accrual_amortization.write", event, target_id, metadata)
    schedule = create_accounting_schedule(request)
    _record_audit(x_actor_id, event, target_id, {**metadata, "schedule_type": schedule.schedule_type})
    return schedule


@router.post("/schedules/{schedule_code}/post")
def post_accrual_amortization_schedule_for_period(
    schedule_code: str,
    request: SchedulePostRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "accrual_amortization.schedule.post"
    target_id = f"accrual-amortization-post:{request.account_set_id}:{request.period}:{schedule_code}"
    metadata = {**_request_metadata(request), "schedule_code": schedule_code}
    _require_permission(x_actor_id, "accrual_amortization.post", event, target_id, metadata)
    entry = post_schedule_for_period(request.account_set_id, schedule_code, request.period, x_actor_id)
    _record_audit(x_actor_id, event, target_id, {**metadata, "journal_entry_id": entry.id})
    return entry


@router.post("/loan-interest")
def post_accrual_amortization_loan_interest(
    request: LoanInterestPostRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "accrual_amortization.loan_interest.post"
    target_id = f"loan-interest:{request.account_set_id}:{request.period}:{request.loan_code}"
    metadata = _request_metadata(request)
    _require_permission(x_actor_id, "accrual_amortization.post", event, target_id, metadata)
    _ensure_loan_schedule(request)
    entry = post_loan_interest_accrual(request.account_set_id, request.loan_code, request.period, x_actor_id)
    _record_audit(x_actor_id, event, target_id, {**metadata, "journal_entry_id": entry.id})
    return entry


def _ensure_loan_schedule(request: LoanInterestPostRequest) -> None:
    try:
        get_loan_schedule(request.account_set_id, request.loan_code)
    except HTTPException as error:
        if error.status_code != 404:
            raise
        create_loan_schedule(
            LoanScheduleCreate(
                account_set_id=request.account_set_id,
                loan_code=request.loan_code,
                principal=request.principal,
                annual_rate=request.annual_rate,
                start_period=request.start_period,
                end_period=request.end_period,
                loan_account_code=request.loan_account_code,
                interest_expense_account_code=request.interest_expense_account_code,
                interest_payable_account_code=request.interest_payable_account_code,
            )
        )


def _request_metadata(request) -> dict[str, str | int | float | bool | None]:
    metadata: dict[str, str | int | float | bool | None] = {
        "account_set_id": request.account_set_id,
        "period": getattr(request, "period", None),
        "schedule_code": getattr(request, "schedule_code", None),
        "loan_code": getattr(request, "loan_code", None),
    }
    if hasattr(request, "total_amount"):
        metadata["amount"] = str(request.total_amount)
    if hasattr(request, "principal"):
        metadata["principal"] = str(request.principal)
        metadata["annual_rate"] = str(request.annual_rate)
    return metadata


def _record_audit(
    actor_id: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
    result: str = "success",
) -> None:
    record_audit_log(
        AuditLogCreateRequest(
            actor_id=actor_id,
            module_id="finance-center",
            event=event,
            target_id=target_id,
            result=result,
            metadata=metadata,
        )
    )


def _require_permission(
    actor_id: str,
    permission_code: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
) -> None:
    if actor_id == "system":
        return

    decision = authorize(actor_id, permission_code)
    if decision.allowed:
        return

    _record_audit(
        actor_id,
        event,
        target_id,
        {
            **metadata,
            "permission_code": permission_code,
            "reason": decision.reason,
        },
        result="denied",
    )
    raise HTTPException(status_code=403, detail=decision.reason)
