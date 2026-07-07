from fastapi import APIRouter, Header, HTTPException, Query

from app.models.system_admin import AuditLogCreateRequest
from app.models.tax_accounting import (
    SurtaxAccrualRequest,
    TaxAmountPostRequest,
    TaxPaymentPostRequest,
    VatLedgerLineListResponse,
)
from app.services.system_admin_service import authorize, record_audit_log
from app.services.tax_accounting_service import (
    build_tax_filing_worksheet,
    calculate_surtax,
    list_vat_ledger_lines,
    post_income_tax_accrual,
    post_surtax_accrual,
    post_tax_payment,
    post_unpaid_vat_transfer,
)


router = APIRouter(prefix="/api/v1/tax-accounting", tags=["tax-accounting"])


@router.get("/vat-ledger")
def get_vat_ledger(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    event = "tax_accounting.vat_ledger.read"
    target_id = f"tax-vat-ledger:{account_set_id}:{period}"
    _require_permission(x_actor_id, "tax_accounting.read", event, target_id, {"account_set_id": account_set_id, "period": period})
    lines = list_vat_ledger_lines(account_set_id, period)
    _record_audit(
        x_actor_id,
        event,
        target_id,
        {"account_set_id": account_set_id, "period": period, "line_count": len(lines)},
    )
    return VatLedgerLineListResponse(account_set_id=account_set_id, period=period, total=len(lines), lines=lines)


@router.get("/filing-worksheet")
def get_tax_filing_worksheet(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    event = "tax_accounting.worksheet.read"
    target_id = f"tax-worksheet:{account_set_id}:{period}"
    _require_permission(x_actor_id, "tax_accounting.read", event, target_id, {"account_set_id": account_set_id, "period": period})
    worksheet = build_tax_filing_worksheet(account_set_id, period)
    _record_audit(
        x_actor_id,
        event,
        target_id,
        {"account_set_id": account_set_id, "period": period, "vat_payable": str(worksheet.vat_payable)},
    )
    return worksheet


@router.post("/unpaid-vat-transfer")
def post_tax_unpaid_vat_transfer(request: TaxAmountPostRequest, x_actor_id: str = Header(default="system")):
    event = "tax_accounting.vat.transfer"
    target_id = f"tax-unpaid-vat-transfer:{request.account_set_id}:{request.period}"
    metadata = _request_metadata(request)
    _require_permission(x_actor_id, "tax_accounting.accrue", event, target_id, metadata)
    entry = post_unpaid_vat_transfer(request.account_set_id, request.period, request.amount, x_actor_id)
    _record_audit(x_actor_id, event, target_id, {**metadata, "journal_entry_id": entry.id})
    return entry


@router.post("/surtax-accrual")
def post_tax_surtax_accrual(request: SurtaxAccrualRequest, x_actor_id: str = Header(default="system")):
    event = "tax_accounting.surtax.accrue"
    target_id = f"tax-surtax-accrual:{request.account_set_id}:{request.period}"
    metadata = _request_metadata(request)
    _require_permission(x_actor_id, "tax_accounting.accrue", event, target_id, metadata)
    surtax = calculate_surtax(
        request.vat_payable,
        request.urban_maintenance_rate,
        request.education_rate,
        request.local_education_rate,
    )
    entry = post_surtax_accrual(request.account_set_id, request.period, surtax, x_actor_id)
    _record_audit(x_actor_id, event, target_id, {**metadata, "journal_entry_id": entry.id, "amount": str(surtax.total)})
    return entry


@router.post("/income-tax-accrual")
def post_tax_income_tax_accrual(request: TaxAmountPostRequest, x_actor_id: str = Header(default="system")):
    event = "tax_accounting.income_tax.accrue"
    target_id = f"tax-income-tax-accrual:{request.account_set_id}:{request.period}"
    metadata = _request_metadata(request)
    _require_permission(x_actor_id, "tax_accounting.accrue", event, target_id, metadata)
    entry = post_income_tax_accrual(request.account_set_id, request.period, request.amount, x_actor_id)
    _record_audit(x_actor_id, event, target_id, {**metadata, "journal_entry_id": entry.id})
    return entry


@router.post("/tax-payments")
def post_tax_payment_entry(request: TaxPaymentPostRequest, x_actor_id: str = Header(default="system")):
    event = "tax_accounting.payment.post"
    target_id = f"tax-payment:{request.account_set_id}:{request.period}:{request.tax_account_code}"
    metadata = _request_metadata(request)
    _require_permission(x_actor_id, "tax_accounting.pay", event, target_id, metadata)
    entry = post_tax_payment(
        account_set_id=request.account_set_id,
        period=request.period,
        tax_account_code=request.tax_account_code,
        amount=request.amount,
        bank_account_code=request.bank_account_code,
        actor_id=x_actor_id,
    )
    _record_audit(x_actor_id, event, target_id, {**metadata, "journal_entry_id": entry.id})
    return entry


def _request_metadata(request) -> dict[str, str | int | float | bool | None]:
    return {
        "account_set_id": request.account_set_id,
        "period": request.period,
        "amount": str(getattr(request, "amount", getattr(request, "vat_payable", ""))),
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
