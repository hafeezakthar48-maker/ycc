from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException

from app.models.accounting import JournalEntryRecord, JournalLineRecord
from app.models.tax_accounting import IncomeTaxCalculationResult, SurtaxCalculationResult, TaxFilingWorksheet, VatLedgerLine
from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.accounting_service import get_chart_of_accounts, list_journal_entries, post_journal_entry


MONEY_QUANT = Decimal("0.01")


def calculate_vat_payable(output_vat: Decimal, input_vat: Decimal, input_transfer_out: Decimal) -> Decimal:
    payable = _money(Decimal(output_vat) - Decimal(input_vat) + Decimal(input_transfer_out))
    return max(payable, Decimal("0.00"))


def list_vat_ledger_lines(account_set_id: str, period: str) -> list[VatLedgerLine]:
    validate_account_set(account_set_id)
    lines: list[VatLedgerLine] = []
    for entry in list_journal_entries(account_set_id, period).entries:
        if entry.status != "posted":
            continue
        for line in entry.lines:
            tax_direction = _vat_direction(line)
            if tax_direction is None:
                continue
            lines.append(
                VatLedgerLine(
                    account_set_id=account_set_id,
                    period=period,
                    tax_direction=tax_direction,
                    invoice_no=_invoice_no(entry),
                    tax_base=_tax_base_amount(entry, tax_direction),
                    tax_amount=_money(line.base_amount),
                    counterparty_id=None,
                    source_journal_entry_id=entry.id,
                )
            )
    lines.sort(key=lambda item: (item.tax_direction, item.invoice_no, item.source_journal_entry_id))
    return lines


def build_tax_filing_worksheet(account_set_id: str, period: str) -> TaxFilingWorksheet:
    vat_lines = list_vat_ledger_lines(account_set_id, period)
    output_vat = _money(sum((line.tax_amount for line in vat_lines if line.tax_direction == "output"), Decimal("0.00")))
    input_vat = _money(sum((line.tax_amount for line in vat_lines if line.tax_direction == "input"), Decimal("0.00")))
    input_transfer_out = _money(
        sum((line.tax_amount for line in vat_lines if line.tax_direction == "input_transfer_out"), Decimal("0.00"))
    )
    vat_payable = calculate_vat_payable(output_vat, input_vat, input_transfer_out)
    entries = list_journal_entries(account_set_id, period).entries
    surtax_payable = _entry_credit_amount(entries, "tax_surtax_accrual", "222103")
    income_tax_payable = _entry_credit_amount(entries, "tax_income_tax_accrual", "222104")
    return TaxFilingWorksheet(
        account_set_id=account_set_id,
        period=period,
        output_vat=output_vat,
        input_vat=input_vat,
        input_transfer_out=input_transfer_out,
        vat_payable=vat_payable,
        surtax_payable=surtax_payable,
        income_tax_payable=income_tax_payable,
    )


def calculate_surtax(
    vat_payable: Decimal,
    urban_maintenance_rate: Decimal,
    education_rate: Decimal,
    local_education_rate: Decimal,
) -> SurtaxCalculationResult:
    urban = _money(Decimal(vat_payable) * Decimal(urban_maintenance_rate))
    education = _money(Decimal(vat_payable) * Decimal(education_rate))
    local = _money(Decimal(vat_payable) * Decimal(local_education_rate))
    return SurtaxCalculationResult(
        urban=urban,
        education=education,
        local=local,
        total=_money(urban + education + local),
    )


def calculate_income_tax_payable(
    accounting_profit: Decimal,
    taxable_increase: Decimal,
    taxable_decrease: Decimal,
    tax_rate: Decimal,
) -> IncomeTaxCalculationResult:
    taxable_income = max(
        _money(Decimal(accounting_profit) + Decimal(taxable_increase) - Decimal(taxable_decrease)),
        Decimal("0.00"),
    )
    income_tax_payable = _money(taxable_income * Decimal(tax_rate))
    return IncomeTaxCalculationResult(
        accounting_profit=_money(accounting_profit),
        taxable_increase=_money(taxable_increase),
        taxable_decrease=_money(taxable_decrease),
        taxable_income=taxable_income,
        tax_rate=Decimal(tax_rate),
        income_tax_payable=income_tax_payable,
    )


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


def post_income_tax_accrual(account_set_id: str, period: str, amount: Decimal, actor_id: str):
    _validate_period_open(account_set_id, period)
    amount = _positive_money(amount, "企业所得税计提金额必须大于 0。")
    source_type = "tax_income_tax_accrual"
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
            description=f"{period} 企业所得税计提",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=[
                _journal_line("6801", account_names, "debit", amount, "计提所得税费用"),
                _journal_line("222104", account_names, "credit", amount, "应交企业所得税"),
            ],
        )
    )


def post_tax_payment(
    account_set_id: str,
    period: str,
    tax_account_code: str,
    amount: Decimal,
    bank_account_code: str,
    actor_id: str,
):
    _validate_period_open(account_set_id, period)
    amount = _positive_money(amount, "纳税支付金额必须大于 0。")
    source_type = "tax_payment"
    source_id = f"{source_type}:{account_set_id}:{period}:{tax_account_code}"
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing is not None:
        return existing

    account_names = _account_names(account_set_id)
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_tax_payment_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} 纳税支付",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=[
                _journal_line(tax_account_code, account_names, "debit", amount, "缴纳税费"),
                _journal_line(bank_account_code, account_names, "credit", amount, "银行支付税费"),
            ],
        )
    )


def post_surtax_accrual(
    account_set_id: str,
    period: str,
    surtax_result: SurtaxCalculationResult,
    actor_id: str,
):
    _validate_period_open(account_set_id, period)
    amount = _positive_money(surtax_result.total, "附加税计提金额必须大于 0。")
    source_type = "tax_surtax_accrual"
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
            description=f"{period} 附加税计提",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=[
                _journal_line("6403", account_names, "debit", amount, "计提税金及附加"),
                _journal_line("222103", account_names, "credit", amount, "应交城建税及教育费附加"),
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


def _vat_direction(line: JournalLineRecord) -> str | None:
    if line.account_code == "22210101" and line.direction == "debit":
        return "input"
    if line.account_code == "22210102" and line.direction == "credit":
        return "output"
    if line.account_code == "22210104" and line.direction == "credit":
        return "input_transfer_out"
    return None


def _tax_base_amount(entry: JournalEntryRecord, tax_direction: str) -> Decimal:
    if tax_direction == "output":
        candidate = next(
            (
                line.base_amount
                for line in entry.lines
                if line.direction == "credit" and line.account_code.startswith(("6001", "6051"))
            ),
            Decimal("0.00"),
        )
    else:
        candidate = next(
            (
                line.base_amount
                for line in entry.lines
                if line.direction == "debit" and not line.account_code.startswith("2221")
            ),
            Decimal("0.00"),
        )
    return _money(candidate)


def _invoice_no(entry: JournalEntryRecord) -> str:
    parts = entry.source_id.split(":")
    return parts[-1] if parts else entry.source_id


def _entry_credit_amount(entries: list[JournalEntryRecord], source_type: str, account_code: str) -> Decimal:
    return _money(
        sum(
            (
                line.base_amount
                for entry in entries
                if entry.status == "posted" and entry.source_type == source_type
                for line in entry.lines
                if line.account_code == account_code and line.direction == "credit"
            ),
            Decimal("0.00"),
        )
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


def _tax_payment_date(period: str) -> str:
    return f"{period}-15"


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
