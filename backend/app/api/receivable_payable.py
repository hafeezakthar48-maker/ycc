from fastapi import APIRouter, Header, Query

from app.models.receivable_payable import CounterpartySettlementCreate
from app.models.system_admin import AuditLogCreateRequest
from app.services.receivable_payable_service import (
    build_aging_report,
    build_counterparty_balances,
    create_counterparty_settlement,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/receivable-payable", tags=["receivable-payable"])


@router.get("/balances")
def get_balances(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    open_item_type: str = Query(pattern="^(receivable|payable)$"),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"{account_set_id}:{period}:{open_item_type}"
    metadata = {"account_set_id": account_set_id, "period": period, "open_item_type": open_item_type}
    _require_rp_permission(
        x_actor_id,
        "receivable_payable.read",
        "receivable_payable.balance.read",
        target_id,
        metadata,
    )
    response = build_counterparty_balances(account_set_id, period, open_item_type)
    _record_rp_audit(
        x_actor_id,
        "receivable_payable.balance.read",
        target_id,
        {**metadata, "item_count": response.item_count, "total_base_balance": str(response.total_base_balance)},
    )
    return response


@router.get("/aging")
def get_aging(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    open_item_type: str = Query(pattern="^(receivable|payable)$"),
    as_of_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"{account_set_id}:{period}:{open_item_type}:{as_of_date}"
    metadata = {
        "account_set_id": account_set_id,
        "period": period,
        "open_item_type": open_item_type,
        "as_of_date": as_of_date,
    }
    _require_rp_permission(
        x_actor_id,
        "receivable_payable.read",
        "receivable_payable.aging.read",
        target_id,
        metadata,
    )
    response = build_aging_report(account_set_id, period, open_item_type, as_of_date)
    _record_rp_audit(
        x_actor_id,
        "receivable_payable.aging.read",
        target_id,
        {**metadata, "total_base_balance": str(response.total_base_balance)},
    )
    return response


@router.post("/settlements")
def create_settlement(request: CounterpartySettlementCreate, x_actor_id: str = Header(default="system")):
    target_id = f"{request.account_set_id}:{request.period}:{request.counterparty_code}"
    metadata = {
        "account_set_id": request.account_set_id,
        "period": request.period,
        "open_item_type": request.open_item_type,
        "counterparty_code": request.counterparty_code,
    }
    _require_rp_permission(
        x_actor_id,
        "receivable_payable.settle",
        "receivable_payable.settle",
        target_id,
        metadata,
    )
    settlement = create_counterparty_settlement(request)
    _record_rp_audit(
        x_actor_id,
        "receivable_payable.settle",
        settlement.settlement_id,
        {**metadata, "amount": str(settlement.total_settled_base_amount)},
    )
    return settlement


def _record_rp_audit(
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


def _require_rp_permission(
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
    _record_rp_audit(
        actor_id,
        event,
        target_id,
        {**metadata, "permission_code": permission_code, "reason": decision.reason},
        result="denied",
    )
    from fastapi import HTTPException

    raise HTTPException(status_code=403, detail=decision.reason)
