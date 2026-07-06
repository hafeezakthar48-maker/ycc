from fastapi import APIRouter, Header, HTTPException

from app.models.payroll import PayrollCalculateRequest
from app.models.system_admin import AuditLogCreateRequest
from app.services.payroll_service import calculate_payroll
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/payroll", tags=["payroll"])


@router.post("/calculate")
def calculate_payroll_record(
    request: PayrollCalculateRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "payroll.calculate"
    target_id = f"payroll:{request.account_set_id}:{request.period}"
    _require_payroll_permission(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": request.account_set_id,
            "period": request.period,
            "employee_count": len(request.employees),
        },
    )
    result = calculate_payroll(request)
    _record_payroll_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": result.account_set_id,
            "period": result.period,
            "employee_count": result.summary.employee_count,
            "gross_pay_total": str(result.summary.gross_pay_total),
            "net_pay_total": str(result.summary.net_pay_total),
            "employer_cost_total": str(result.summary.employer_cost_total),
        },
    )
    return result


def _record_payroll_audit(
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


def _require_payroll_permission(
    actor_id: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
) -> None:
    if actor_id == "system":
        return

    permission_code = "payroll.calculate"
    decision = authorize(actor_id, permission_code)
    if decision.allowed:
        return

    _record_payroll_audit(
        actor_id=actor_id,
        event=event,
        target_id=target_id,
        result="denied",
        metadata={
            **metadata,
            "permission_code": permission_code,
            "reason": decision.reason,
        },
    )
    raise HTTPException(status_code=403, detail=decision.reason)
