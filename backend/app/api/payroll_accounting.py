from fastapi import APIRouter, Header, HTTPException, Query

from app.models.payroll_accounting import (
    PayrollAccountingPostRequest,
    PayrollLiabilityPaymentPostRequest,
    PayrollPaymentPostRequest,
)
from app.models.system_admin import AuditLogCreateRequest
from app.services.payroll_accounting_service import (
    accrue_payroll_batch,
    list_payroll_accounting_batches,
    pay_payroll_batch,
    remit_payroll_liabilities,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/payroll-accounting", tags=["payroll-accounting"])


@router.get("/batches")
def get_payroll_accounting_batches(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    event = "payroll_accounting.batch.read"
    target_id = f"payroll-accounting:{account_set_id}:{period}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="payroll_accounting.read",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id, "period": period},
    )
    result = list_payroll_accounting_batches(account_set_id, period)
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id, "period": period, "batch_count": result.total},
    )
    return result


@router.post("/accruals")
def post_payroll_accrual(
    request: PayrollAccountingPostRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "payroll_accounting.accrual.post"
    target_id = f"payroll-accrual:{request.account_set_id}:{request.period}:{request.payroll_batch_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="payroll_accounting.accrue",
        event=event,
        target_id=target_id,
        metadata=_request_metadata(request),
    )
    entry = accrue_payroll_batch(request.account_set_id, request.period, request.payroll_batch_id, x_actor_id)
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**_request_metadata(request), "journal_entry_id": entry.id},
    )
    return entry


@router.post("/payments")
def post_payroll_payment(
    request: PayrollPaymentPostRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "payroll_accounting.payment.post"
    target_id = f"payroll-payment:{request.account_set_id}:{request.period}:{request.payroll_batch_id}"
    metadata = {**_request_metadata(request), "bank_account_code": request.bank_account_code}
    _require_permission(
        actor_id=x_actor_id,
        permission_code="payroll_accounting.pay",
        event=event,
        target_id=target_id,
        metadata=metadata,
    )
    entry = pay_payroll_batch(
        request.account_set_id,
        request.period,
        request.payroll_batch_id,
        request.bank_account_code,
        x_actor_id,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**metadata, "journal_entry_id": entry.id},
    )
    return entry


@router.post("/liability-payments")
def post_payroll_liability_payment(
    request: PayrollLiabilityPaymentPostRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "payroll_accounting.liability_payment.post"
    target_id = f"payroll-liability-payment:{request.account_set_id}:{request.period}:{request.payroll_batch_id}"
    metadata = {**_request_metadata(request), "bank_account_code": request.bank_account_code}
    _require_permission(
        actor_id=x_actor_id,
        permission_code="payroll_accounting.remit",
        event=event,
        target_id=target_id,
        metadata=metadata,
    )
    entry = remit_payroll_liabilities(
        request.account_set_id,
        request.period,
        request.payroll_batch_id,
        request.bank_account_code,
        x_actor_id,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**metadata, "journal_entry_id": entry.id},
    )
    return entry


def _request_metadata(request: PayrollAccountingPostRequest) -> dict[str, str]:
    return {
        "account_set_id": request.account_set_id,
        "period": request.period,
        "payroll_batch_id": request.payroll_batch_id,
    }


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
