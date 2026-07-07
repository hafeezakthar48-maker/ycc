from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException

from app.models.accounting import JournalEntryCreate, JournalEntryRecord, JournalLineCreate
from app.models.payroll_accounting import PayrollAccountingBatch, PayrollAccountingBatchCreate
from app.services.accounting_period_service import validate_account_set
from app.services.accounting_service import get_chart_of_accounts, list_journal_entries, post_journal_entry
from app.services.payroll_service import get_payroll_calculation


MONEY_QUANT = Decimal("0.01")


def get_payroll_accounting_batch(
    account_set_id: str,
    period: str,
    payroll_batch_id: str,
) -> PayrollAccountingBatch:
    validate_account_set(account_set_id)
    calculation = get_payroll_calculation(account_set_id, period)
    if calculation is None:
        raise HTTPException(status_code=404, detail="工资批次不存在或尚未计算。")

    summary = calculation.summary
    create_payload = PayrollAccountingBatchCreate(
        account_set_id=account_set_id,
        period=period,
        payroll_batch_id=payroll_batch_id,
        gross_salary=_money(summary.gross_pay_total),
        employee_social_security=_money(summary.employee_social_security_total),
        employee_housing_fund=_money(summary.employee_housing_fund_total),
        individual_income_tax=_money(summary.individual_income_tax_total),
        net_salary=_money(summary.net_pay_total),
        employer_social_security=_money(summary.employer_social_security_total),
        employer_housing_fund=_money(summary.employer_housing_fund_total),
    )
    accrual_entry = _existing_entry(account_set_id, period, "payroll_accrual", _source_id("payroll_accrual", account_set_id, period, payroll_batch_id))
    payment_entry = _existing_entry(account_set_id, period, "payroll_payment", _source_id("payroll_payment", account_set_id, period, payroll_batch_id))
    status = "paid" if payment_entry else "accrued" if accrual_entry else "calculated"
    return PayrollAccountingBatch(
        **create_payload.model_dump(),
        status=status,
        accrual_journal_entry_id=accrual_entry.id if accrual_entry else None,
        payment_journal_entry_id=payment_entry.id if payment_entry else None,
    )


def build_payroll_accrual_lines(batch: PayrollAccountingBatch) -> list[JournalLineCreate]:
    employer_cost = _money(batch.employer_social_security + batch.employer_housing_fund)
    return _journal_lines(
        batch.account_set_id,
        [
            ("6602", "debit", batch.gross_salary, "计提工资"),
            ("6602", "debit", employer_cost, "计提企业社保公积金"),
            ("2211", "credit", batch.gross_salary, "应付职工薪酬-工资"),
            ("2211", "credit", employer_cost, "应付职工薪酬-社保公积金"),
        ],
    )


def accrue_payroll_batch(
    account_set_id: str,
    period: str,
    payroll_batch_id: str,
    actor_id: str,
) -> JournalEntryRecord:
    source_type = "payroll_accrual"
    source_id = _source_id(source_type, account_set_id, period, payroll_batch_id)
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing:
        return existing

    batch = get_payroll_accounting_batch(account_set_id, period, payroll_batch_id)
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} 工资薪酬计提",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=build_payroll_accrual_lines(batch),
        )
    )


def build_payroll_payment_lines(batch: PayrollAccountingBatch, bank_account_code: str) -> list[JournalLineCreate]:
    employee_deductions = _money(
        batch.employee_social_security + batch.employee_housing_fund + batch.individual_income_tax
    )
    return _journal_lines(
        batch.account_set_id,
        [
            ("2211", "debit", batch.gross_salary, "冲减应付工资"),
            ("2241", "credit", batch.employee_social_security + batch.employee_housing_fund, "代扣个人社保公积金"),
            ("2221", "credit", batch.individual_income_tax, "代扣个人所得税"),
            (bank_account_code, "credit", batch.gross_salary - employee_deductions, "发放实发工资"),
        ],
    )


def pay_payroll_batch(
    account_set_id: str,
    period: str,
    payroll_batch_id: str,
    bank_account_code: str,
    actor_id: str,
) -> JournalEntryRecord:
    source_type = "payroll_payment"
    source_id = _source_id(source_type, account_set_id, period, payroll_batch_id)
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing:
        return existing

    batch = get_payroll_accounting_batch(account_set_id, period, payroll_batch_id)
    if batch.accrual_journal_entry_id is None:
        raise HTTPException(status_code=409, detail="工资批次尚未计提，不能发放工资。")
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} 工资发放",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=build_payroll_payment_lines(batch, bank_account_code),
        )
    )


def _source_id(source_type: str, account_set_id: str, period: str, payroll_batch_id: str) -> str:
    return f"{source_type}:{account_set_id}:{period}:{payroll_batch_id}"


def _existing_entry(
    account_set_id: str,
    period: str,
    source_type: str,
    source_id: str,
) -> JournalEntryRecord | None:
    return next(
        (
            entry
            for entry in list_journal_entries(account_set_id, period).entries
            if entry.status == "posted" and entry.source_type == source_type and entry.source_id == source_id
        ),
        None,
    )


def _journal_lines(
    account_set_id: str,
    rows: list[tuple[str, str, Decimal, str]],
) -> list[JournalLineCreate]:
    account_names = {account.account_code: account.account_name for account in get_chart_of_accounts(account_set_id).accounts}
    return [
        JournalLineCreate(
            account_code=account_code,
            account_name=account_names.get(account_code, account_code),
            direction=direction,  # type: ignore[arg-type]
            currency="CNY",
            original_amount=_money(amount),
            exchange_rate=Decimal("1.000000"),
            base_amount=_money(amount),
            description=description,
        )
        for account_code, direction, amount, description in rows
        if _money(amount) > Decimal("0.00")
    ]


def _period_end_date(period: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    return f"{period}-{monthrange(year, month)[1]:02d}"


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
