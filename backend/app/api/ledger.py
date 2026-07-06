from fastapi import APIRouter, Header, HTTPException, Path, Query

from app.models.accounting_period import PeriodStatusChangeRequest
from app.models.system_admin import AuditLogCreateRequest
from app.services.accounting_period_service import (
    close_accounting_period,
    list_account_sets,
    list_accounting_periods,
    reopen_accounting_period,
)
from app.services.ledger_service import build_account_balance_table, build_detail_ledger, build_general_ledger
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])
PERIOD_QUERY = Query(pattern=r"^\d{4}-\d{2}$")
PERIOD_PATH = Path(pattern=r"^\d{4}-\d{2}$")


@router.get("/account-sets")
def get_account_sets(x_actor_id: str = Header(default="system")):
    event = "ledger.account_sets.read"
    target_id = "ledger-account-sets"
    _require_ledger_permission(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={},
    )
    account_sets = list_account_sets()
    _record_ledger_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_count": len(account_sets.account_sets)},
    )
    return account_sets


@router.get("/periods")
def get_accounting_periods(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "ledger.periods.read"
    target_id = f"ledger-periods:{account_set_id}"
    _require_ledger_permission(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id},
    )
    periods = list_accounting_periods(account_set_id)
    _record_ledger_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_id": periods.account_set_id, "period_count": len(periods.periods)},
    )
    return periods


@router.post("/periods/{period}/close")
def close_period(
    request: PeriodStatusChangeRequest,
    period: str = PERIOD_PATH,
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "ledger.period.close"
    target_id = f"ledger-period:{account_set_id}:{period}"
    _require_ledger_manage_permission(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id, "period": period},
    )
    closed = close_accounting_period(period, request.operator, account_set_id)
    _record_ledger_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": closed.account_set_id,
            "period": closed.period,
            "status": closed.status,
            "operator": request.operator,
        },
    )
    return closed


@router.post("/periods/{period}/reopen")
def reopen_period(
    request: PeriodStatusChangeRequest,
    period: str = PERIOD_PATH,
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "ledger.period.reopen"
    target_id = f"ledger-period:{account_set_id}:{period}"
    _require_ledger_manage_permission(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id, "period": period},
    )
    reopened = reopen_accounting_period(period, request.operator, account_set_id)
    _record_ledger_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": reopened.account_set_id,
            "period": reopened.period,
            "status": reopened.status,
            "operator": request.operator,
        },
    )
    return reopened


@router.get("/general")
def get_general_ledger(
    period: str = PERIOD_QUERY,
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "ledger.general.read"
    target_id = _ledger_target("ledger-general", account_set_id, period)
    _require_ledger_permission(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"period": period, "account_set_id": account_set_id},
    )
    ledger = build_general_ledger(period, account_set_id)
    _record_ledger_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "period": ledger.period,
            "account_set_id": account_set_id,
            "voucher_count": ledger.voucher_count,
            "entry_count": ledger.entry_count,
            "balanced": ledger.balanced,
        },
    )
    return ledger


@router.get("/detail")
def get_detail_ledger(
    period: str = PERIOD_QUERY,
    account_code: str = Query(min_length=1, max_length=32),
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    dimension_type: str | None = Query(default=None, max_length=40),
    dimension_code: str | None = Query(default=None, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "ledger.detail.read"
    target_id = _ledger_target("ledger-detail", account_set_id, period, account_code)
    _require_ledger_permission(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "period": period,
            "account_set_id": account_set_id,
            "account_code": account_code,
            "dimension_type": dimension_type,
            "dimension_code": dimension_code,
        },
    )
    ledger = build_detail_ledger(
        period,
        account_code,
        account_set_id,
        dimension_type=dimension_type,
        dimension_code=dimension_code,
    )
    _record_ledger_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "period": ledger.period,
            "account_set_id": account_set_id,
            "account_code": ledger.account_code,
            "account_name": ledger.account_name,
            "line_count": ledger.line_count,
            "balance_direction": ledger.balance_direction,
            "dimension_type": dimension_type,
            "dimension_code": dimension_code,
        },
    )
    return ledger


@router.get("/account-balances")
def get_account_balance_table(
    period: str = PERIOD_QUERY,
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "ledger.account_balances.read"
    target_id = _ledger_target("ledger-account-balances", account_set_id, period)
    _require_ledger_permission(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"period": period, "account_set_id": account_set_id},
    )
    balance_table = build_account_balance_table(period, account_set_id)
    _record_ledger_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "period": balance_table.period,
            "account_set_id": account_set_id,
            "account_count": balance_table.account_count,
            "balanced": balance_table.balanced,
        },
    )
    return balance_table


def _ledger_target(prefix: str, account_set_id: str, *parts: str) -> str:
    suffix = ":".join(parts)
    if account_set_id == "default":
        return f"{prefix}:{suffix}"
    return f"{prefix}:{account_set_id}:{suffix}"


def _record_ledger_audit(
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


def _require_ledger_permission(
    actor_id: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
) -> None:
    if actor_id == "system":
        return

    decision = authorize(actor_id, "ledger.read")
    if decision.allowed:
        return

    _record_ledger_audit(
        actor_id=actor_id,
        event=event,
        target_id=target_id,
        result="denied",
        metadata={
            **metadata,
            "permission_code": "ledger.read",
            "reason": decision.reason,
        },
    )
    raise HTTPException(status_code=403, detail=decision.reason)


def _require_ledger_manage_permission(
    actor_id: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
) -> None:
    if actor_id == "system":
        return

    permission_code = "ledger.period.manage"
    decision = authorize(actor_id, permission_code)
    if decision.allowed:
        return

    _record_ledger_audit(
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
