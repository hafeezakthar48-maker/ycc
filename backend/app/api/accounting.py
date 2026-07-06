from fastapi import APIRouter, Header, HTTPException, Query

from app.models.system_admin import AuditLogCreateRequest
from app.services.accounting_service import get_chart_of_accounts, get_journal_entry, list_journal_entries
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/accounting", tags=["accounting"])


@router.get("/accounts")
def get_accounts(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    _require_accounting_permission(
        x_actor_id,
        "accounting.account.read",
        "accounting.account.read",
        f"accounts:{account_set_id}",
        {"account_set_id": account_set_id},
    )
    response = get_chart_of_accounts(account_set_id)
    _record_accounting_audit(
        x_actor_id,
        "accounting.account.read",
        f"accounts:{account_set_id}",
        {"account_set_id": account_set_id, "account_count": len(response.accounts)},
    )
    return response


@router.get("/journal-entries")
def get_journal_entries(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"journal-entries:{account_set_id}:{period or 'all'}"
    metadata = {"account_set_id": account_set_id, "period": period}
    _require_accounting_permission(x_actor_id, "accounting.entry.read", "accounting.entry.read", target_id, metadata)
    response = list_journal_entries(account_set_id, period)
    _record_accounting_audit(
        x_actor_id,
        "accounting.entry.read",
        target_id,
        {**metadata, "entry_count": response.total},
    )
    return response


@router.get("/journal-entries/{entry_id}")
def get_journal_entry_detail(entry_id: str, x_actor_id: str = Header(default="system")):
    target_id = f"journal-entry:{entry_id}"
    _require_accounting_permission(
        x_actor_id,
        "accounting.entry.read",
        "accounting.entry.read",
        target_id,
        {"entry_id": entry_id},
    )
    entry = get_journal_entry(entry_id)
    _record_accounting_audit(
        x_actor_id,
        "accounting.entry.read",
        target_id,
        {"entry_id": entry_id, "account_set_id": entry.account_set_id, "period": entry.period},
    )
    return entry


def _record_accounting_audit(
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


def _require_accounting_permission(
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
    _record_accounting_audit(
        actor_id,
        event,
        target_id,
        {**metadata, "permission_code": permission_code, "reason": decision.reason},
        result="denied",
    )
    raise HTTPException(status_code=403, detail=decision.reason)
