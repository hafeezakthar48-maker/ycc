from fastapi import APIRouter, Header, HTTPException, Query

from app.models.accounting import ExchangeRateCreate, JournalEntryCreate
from app.models.system_admin import AuditLogCreateRequest
from app.services.accounting_service import (
    get_chart_of_accounts,
    get_journal_entry,
    list_currencies,
    list_exchange_rates,
    list_journal_entries,
    post_journal_entry,
    upsert_exchange_rate,
)
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


@router.get("/currencies")
def get_currencies(x_actor_id: str = Header(default="system")):
    _require_accounting_permission(
        x_actor_id,
        "accounting.currency.read",
        "accounting.currency.read",
        "currencies",
        {},
    )
    response = list_currencies()
    _record_accounting_audit(
        x_actor_id,
        "accounting.currency.read",
        "currencies",
        {"currency_count": len(response.currencies)},
    )
    return response


@router.get("/exchange-rates")
def get_exchange_rates(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"exchange-rates:{account_set_id}"
    metadata = {"account_set_id": account_set_id}
    _require_accounting_permission(
        x_actor_id,
        "accounting.exchange_rate.read",
        "accounting.exchange_rate.read",
        target_id,
        metadata,
    )
    response = list_exchange_rates(account_set_id)
    _record_accounting_audit(
        x_actor_id,
        "accounting.exchange_rate.read",
        target_id,
        {**metadata, "rate_count": len(response.rates)},
    )
    return response


@router.post("/exchange-rates")
def create_exchange_rate(request: ExchangeRateCreate, x_actor_id: str = Header(default="system")):
    target_id = f"exchange-rate:{request.account_set_id}:{request.rate_date}:{request.source_currency}"
    metadata = {
        "account_set_id": request.account_set_id,
        "rate_date": request.rate_date,
        "source_currency": request.source_currency,
    }
    _require_accounting_permission(
        x_actor_id,
        "accounting.exchange_rate.write",
        "accounting.exchange_rate.write",
        target_id,
        metadata,
    )
    response = upsert_exchange_rate(request)
    _record_accounting_audit(
        x_actor_id,
        "accounting.exchange_rate.write",
        response.id,
        {
            "account_set_id": response.account_set_id,
            "rate_date": response.rate_date,
            "source_currency": response.source_currency,
            "target_currency": response.target_currency,
        },
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


@router.post("/journal-entries")
def create_journal_entry(request: JournalEntryCreate, x_actor_id: str = Header(default="system")):
    target_id = f"journal-entry-source:{request.source_type}:{request.source_id}"
    metadata = {
        "account_set_id": request.account_set_id,
        "source_type": request.source_type,
        "source_id": request.source_id,
    }
    _require_accounting_permission(
        x_actor_id,
        "accounting.entry.post",
        "accounting.entry.post",
        target_id,
        metadata,
    )
    entry = post_journal_entry(request)
    _record_accounting_audit(
        x_actor_id,
        "accounting.entry.post",
        entry.id,
        {"account_set_id": entry.account_set_id, "period": entry.period, "entry_number": entry.entry_number},
    )
    return entry


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
