from dataclasses import dataclass
from decimal import Decimal
import re

from app.models.ledger import (
    AccountBalanceTableResponse,
    DetailLedgerResponse,
    GeneralLedgerResponse,
    LedgerAccountSummary,
    LedgerDetailLine,
)
from app.models.voucher_center import VoucherCenterRecord
from app.services.accounting_service import list_journal_entries
from app.services.voucher_center_service import list_vouchers


PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")
ZERO = Decimal("0.00")
ONE_RATE = Decimal("1.000000")


@dataclass
class _AccountAccumulator:
    account_code: str
    account_name: str
    debit_total: Decimal = ZERO
    credit_total: Decimal = ZERO
    entry_count: int = 0


def build_general_ledger(period: str, account_set_id: str = "default") -> GeneralLedgerResponse:
    _validate_period(period)
    formal_entries = list_journal_entries(account_set_id, period).entries
    if formal_entries:
        accounts = _build_account_summaries_from_journal_entries(formal_entries)
        total_debit = sum((account.debit_total for account in accounts), ZERO)
        total_credit = sum((account.credit_total for account in accounts), ZERO)
        return GeneralLedgerResponse(
            source="formal_journal_entries",
            period=period,
            voucher_count=len({entry.source_id for entry in formal_entries if entry.source_type == "voucher_center"}),
            entry_count=sum(account.entry_count for account in accounts),
            total_debit=total_debit,
            total_credit=total_credit,
            balanced=total_debit == total_credit,
            accounts=accounts,
        )

    vouchers = _reviewed_vouchers_in_period(period, account_set_id)
    accounts = _build_account_summaries(vouchers)
    total_debit = sum((account.debit_total for account in accounts), ZERO)
    total_credit = sum((account.credit_total for account in accounts), ZERO)
    return GeneralLedgerResponse(
        period=period,
        voucher_count=len(vouchers),
        entry_count=sum(account.entry_count for account in accounts),
        total_debit=total_debit,
        total_credit=total_credit,
        balanced=total_debit == total_credit,
        accounts=accounts,
    )


def build_detail_ledger(
    period: str,
    account_code: str,
    account_set_id: str = "default",
    dimension_type: str | None = None,
    dimension_code: str | None = None,
) -> DetailLedgerResponse:
    _validate_period(period)
    formal_entries = list_journal_entries(account_set_id, period).entries
    if formal_entries:
        lines = [
            detail_line
            for entry in formal_entries
            for detail_line in _journal_detail_lines(entry, dimension_type, dimension_code)
            if detail_line.account_code == account_code
        ]
        lines.sort(key=lambda line: (line.voucher_date, line.voucher_number, line.account_code))
        debit_total = sum((line.debit_amount for line in lines), ZERO)
        credit_total = sum((line.credit_amount for line in lines), ZERO)
        balance_direction, balance_amount = _balance(debit_total, credit_total)
        return DetailLedgerResponse(
            source="formal_journal_entries",
            period=period,
            account_code=account_code,
            account_name=lines[0].account_name if lines else "",
            line_count=len(lines),
            debit_total=debit_total,
            credit_total=credit_total,
            balance_direction=balance_direction,
            balance_amount=balance_amount,
            lines=lines,
        )

    vouchers = _reviewed_vouchers_in_period(period, account_set_id)
    lines = [
        detail_line
        for voucher in vouchers
        for detail_line in _voucher_detail_lines(voucher)
        if detail_line.account_code == account_code
    ]
    lines.sort(key=lambda line: (line.voucher_date, line.voucher_number, line.account_code))
    debit_total = sum((line.debit_amount for line in lines), ZERO)
    credit_total = sum((line.credit_amount for line in lines), ZERO)
    balance_direction, balance_amount = _balance(debit_total, credit_total)
    return DetailLedgerResponse(
        period=period,
        account_code=account_code,
        account_name=lines[0].account_name if lines else "",
        line_count=len(lines),
        debit_total=debit_total,
        credit_total=credit_total,
        balance_direction=balance_direction,
        balance_amount=balance_amount,
        lines=lines,
    )


def build_account_balance_table(period: str, account_set_id: str = "default") -> AccountBalanceTableResponse:
    general_ledger = build_general_ledger(period, account_set_id)
    return AccountBalanceTableResponse(
        source=general_ledger.source,
        period=general_ledger.period,
        account_count=len(general_ledger.accounts),
        total_debit=general_ledger.total_debit,
        total_credit=general_ledger.total_credit,
        balanced=general_ledger.balanced,
        accounts=general_ledger.accounts,
    )


def _reviewed_vouchers_in_period(period: str, account_set_id: str) -> list[VoucherCenterRecord]:
    from app.services.accounting_period_service import validate_account_set

    _validate_period(period)
    validate_account_set(account_set_id)
    return [
        voucher
        for voucher in list_vouchers(account_set_id).vouchers
        if voucher.status == "reviewed" and voucher.voucher_date.startswith(f"{period}-")
    ]


def _build_account_summaries(vouchers: list[VoucherCenterRecord]) -> list[LedgerAccountSummary]:
    accounts: dict[str, _AccountAccumulator] = {}
    for voucher in vouchers:
        for line in voucher.lines:
            debit_amount, credit_amount = _line_debit_credit(line.direction, line.amount)
            account = accounts.setdefault(
                line.account_code,
                _AccountAccumulator(account_code=line.account_code, account_name=line.account_name),
            )
            account.debit_total += debit_amount
            account.credit_total += credit_amount
            account.entry_count += 1

    summaries = []
    for account in sorted(accounts.values(), key=lambda item: item.account_code):
        balance_direction, balance_amount = _balance(account.debit_total, account.credit_total)
        summaries.append(
            LedgerAccountSummary(
                account_code=account.account_code,
                account_name=account.account_name,
                debit_total=account.debit_total,
                credit_total=account.credit_total,
                balance_direction=balance_direction,
                balance_amount=balance_amount,
                entry_count=account.entry_count,
            )
        )
    return summaries


def _build_account_summaries_from_journal_entries(entries) -> list[LedgerAccountSummary]:
    accounts: dict[str, _AccountAccumulator] = {}
    for entry in entries:
        for line in entry.lines:
            debit_amount, credit_amount = _journal_line_debit_credit(line.direction, line.base_amount)
            account = accounts.setdefault(
                line.account_code,
                _AccountAccumulator(account_code=line.account_code, account_name=line.account_name),
            )
            account.debit_total += debit_amount
            account.credit_total += credit_amount
            account.entry_count += 1

    summaries = []
    for account in sorted(accounts.values(), key=lambda item: item.account_code):
        balance_direction, balance_amount = _balance(account.debit_total, account.credit_total)
        summaries.append(
            LedgerAccountSummary(
                account_code=account.account_code,
                account_name=account.account_name,
                debit_total=account.debit_total,
                credit_total=account.credit_total,
                balance_direction=balance_direction,
                balance_amount=balance_amount,
                entry_count=account.entry_count,
            )
        )
    return summaries


def _voucher_detail_lines(voucher: VoucherCenterRecord) -> list[LedgerDetailLine]:
    detail_lines = []
    for line in voucher.lines:
        debit_amount, credit_amount = _line_debit_credit(line.direction, line.amount)
        detail_lines.append(
            LedgerDetailLine(
                voucher_id=voucher.id,
                voucher_number=voucher.voucher_number,
                voucher_date=voucher.voucher_date,
                summary=voucher.summary,
                counterparty=voucher.counterparty,
                account_code=line.account_code,
                account_name=line.account_name,
                direction=line.direction,
                explanation=line.explanation,
                currency="CNY",
                original_amount=line.amount,
                exchange_rate=ONE_RATE,
                debit_amount=debit_amount,
                credit_amount=credit_amount,
                status=voucher.status,
            )
        )
    return detail_lines


def _journal_detail_lines(
    entry,
    dimension_type: str | None = None,
    dimension_code: str | None = None,
) -> list[LedgerDetailLine]:
    detail_lines = []
    for line in entry.lines:
        if not _line_matches_dimension(line, dimension_type, dimension_code):
            continue
        debit_amount, credit_amount = _journal_line_debit_credit(line.direction, line.base_amount)
        detail_lines.append(
            LedgerDetailLine(
                voucher_id=entry.source_id if entry.source_type == "voucher_center" else entry.id,
                voucher_number=entry.entry_number,
                voucher_date=entry.entry_date,
                summary=entry.description,
                counterparty="",
                account_code=line.account_code,
                account_name=line.account_name,
                direction="借" if line.direction == "debit" else "贷",
                explanation=line.description,
                currency=line.currency,
                original_amount=line.original_amount,
                exchange_rate=line.exchange_rate,
                dimensions=[
                    {
                        "dimension_type": dimension.dimension_type,
                        "dimension_code": dimension.dimension_code,
                        "dimension_name": dimension.dimension_name,
                    }
                    for dimension in line.dimensions
                ],
                debit_amount=debit_amount,
                credit_amount=credit_amount,
                status=entry.status,
            )
        )
    return detail_lines


def _line_matches_dimension(line, dimension_type: str | None, dimension_code: str | None) -> bool:
    if not dimension_type and not dimension_code:
        return True
    return any(
        dimension.dimension_type == dimension_type and dimension.dimension_code == dimension_code
        for dimension in line.dimensions
    )


def _line_debit_credit(direction: str, amount: Decimal) -> tuple[Decimal, Decimal]:
    if direction == "借":
        return amount, ZERO
    return ZERO, amount


def _journal_line_debit_credit(direction: str, amount: Decimal) -> tuple[Decimal, Decimal]:
    if direction == "debit":
        return amount, ZERO
    return ZERO, amount


def _balance(debit_total: Decimal, credit_total: Decimal) -> tuple[str, Decimal]:
    if debit_total > credit_total:
        return "借", debit_total - credit_total
    if credit_total > debit_total:
        return "贷", credit_total - debit_total
    return "平", ZERO


def _validate_period(period: str) -> None:
    if not PERIOD_PATTERN.fullmatch(period):
        raise ValueError("账簿期间格式应为 YYYY-MM。")
