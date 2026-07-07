from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.accounting_service import get_chart_of_accounts, list_journal_entries, post_journal_entry


MONEY_QUANT = Decimal("0.01")


def calculate_vat_payable(output_vat: Decimal, input_vat: Decimal, input_transfer_out: Decimal) -> Decimal:
    payable = _money(Decimal(output_vat) - Decimal(input_vat) + Decimal(input_transfer_out))
    return max(payable, Decimal("0.00"))


def post_unpaid_vat_transfer(account_set_id: str, period: str, amount: Decimal, actor_id: str):
    _validate_period_open(account_set_id, period)
    amount = _positive_money(amount, "未交增值税结转金额必须大于 0。")
    source_type = "tax_unpaid_vat_transfer"
    source_id = f"{source_type}:{account_set_id}:{period}"
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing is not None:
        return existing

    account_names = _account_names(account_set_id)
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} 转出未交增值税",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=[
                _journal_line(
                    account_code="22210103",
                    account_names=account_names,
                    direction="debit",
                    amount=amount,
                    description="转出未交增值税",
                ),
                _journal_line(
                    account_code="222102",
                    account_names=account_names,
                    direction="credit",
                    amount=amount,
                    description="转入未交增值税",
                ),
            ],
        )
    )


def _validate_period_open(account_set_id: str, period: str) -> None:
    validate_account_set(account_set_id)
    if is_accounting_period_closed(period, account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能生成税务正式分录。")


def _existing_entry(account_set_id: str, period: str, source_type: str, source_id: str):
    return next(
        (
            entry
            for entry in list_journal_entries(account_set_id, period).entries
            if entry.status == "posted" and entry.source_type == source_type and entry.source_id == source_id
        ),
        None,
    )


def _journal_line(
    account_code: str,
    account_names: dict[str, str],
    direction: str,
    amount: Decimal,
    description: str,
) -> JournalLineCreate:
    return JournalLineCreate(
        account_code=account_code,
        account_name=account_names.get(account_code, account_code),
        direction=direction,  # type: ignore[arg-type]
        original_amount=_money(amount),
        base_amount=_money(amount),
        description=description,
    )


def _positive_money(value: Decimal, message: str) -> Decimal:
    amount = _money(value)
    if amount <= Decimal("0.00"):
        raise HTTPException(status_code=422, detail=message)
    return amount


def _account_names(account_set_id: str) -> dict[str, str]:
    return {account.account_code: account.account_name for account in get_chart_of_accounts(account_set_id).accounts}


def _period_end_date(period: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    return f"{period}-{monthrange(year, month)[1]:02d}"


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
