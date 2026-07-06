from decimal import Decimal
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.models.bank_reconciliation import (
    BankBalanceReconciliationStatement,
    BankMatchCandidate,
    BankMatchCandidateResponse,
    BankReconciliationConfirmRequest,
    BankReconciliationMatch,
    BankStatementImportResult,
    BankStatementLine,
    BankStatementLineCreate,
)
from app.services.accounting_service import list_cash_journal_lines
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.receivable_payable_service import create_counterparty_settlement


ZERO = Decimal("0.00")
_BANK_STATEMENT_LINES: dict[str, BankStatementLine] = {}
_BANK_RECONCILIATION_MATCHES: dict[str, BankReconciliationMatch] = {}


def reset_bank_reconciliation_store() -> None:
    _BANK_STATEMENT_LINES.clear()
    _BANK_RECONCILIATION_MATCHES.clear()


def import_bank_statement_lines(
    account_set_id: str,
    lines: list[BankStatementLineCreate],
) -> BankStatementImportResult:
    validate_account_set(account_set_id)
    imported: list[BankStatementLine] = []
    duplicate_count = 0
    for line in lines:
        if line.account_set_id != account_set_id:
            raise ValueError("银行流水账套与导入账套不一致。")
        key = _statement_key(line)
        if key in _BANK_STATEMENT_LINES:
            duplicate_count += 1
            continue
        saved = BankStatementLine(
            **line.model_dump(),
            statement_line_id=f"bankline-{uuid4().hex[:12]}",
            imported_at=_now(),
        )
        _BANK_STATEMENT_LINES[key] = saved
        imported.append(saved)
    return BankStatementImportResult(
        account_set_id=account_set_id,
        imported_count=len(imported),
        duplicate_count=duplicate_count,
        lines=imported,
    )


def suggest_bank_matches(
    account_set_id: str,
    bank_account_id: str,
    period: str,
    minimum_score: int = 80,
) -> BankMatchCandidateResponse:
    validate_account_set(account_set_id)
    statement_lines = [
        line
        for line in _BANK_STATEMENT_LINES.values()
        if line.account_set_id == account_set_id
        and line.bank_account_id == bank_account_id
        and line.transaction_date[:7] == period
        and line.match_status != "matched"
    ]
    journal_lines = list_cash_journal_lines(account_set_id, period)
    candidates: list[BankMatchCandidate] = []
    for statement_line in statement_lines:
        for journal_line in journal_lines:
            if statement_line.direction != journal_line["cash_direction"]:
                continue
            if statement_line.currency != journal_line["currency"]:
                continue
            score, reasons = _score_match(statement_line, journal_line)
            if score < minimum_score:
                continue
            candidates.append(
                BankMatchCandidate(
                    statement_line_id=statement_line.statement_line_id,
                    journal_entry_id=journal_line["entry_id"],
                    journal_line_id=journal_line["line_id"],
                    direction=statement_line.direction,
                    score=score,
                    reasons=reasons,
                    statement_date=statement_line.transaction_date,
                    journal_date=journal_line["entry_date"],
                    statement_amount=statement_line.amount,
                    journal_amount=journal_line["base_amount"],
                    currency=statement_line.currency,
                    counterparty_name=statement_line.counterparty_name,
                    summary=statement_line.summary,
                )
            )
    candidates.sort(key=lambda item: (-item.score, item.statement_date, item.statement_line_id, item.journal_line_id))
    return BankMatchCandidateResponse(
        account_set_id=account_set_id,
        bank_account_id=bank_account_id,
        period=period,
        minimum_score=minimum_score,
        candidates=candidates,
    )


def confirm_bank_reconciliation(request: BankReconciliationConfirmRequest) -> BankReconciliationMatch:
    validate_account_set(request.account_set_id)
    if is_accounting_period_closed(request.period, request.account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能新增银行对账确认。")

    statement_lines = _get_statement_lines(request.account_set_id, request.bank_account_id, request.period)
    statement_by_id = {line.statement_line_id: line for line in statement_lines}
    missing_statement_ids = [line_id for line_id in request.statement_line_ids if line_id not in statement_by_id]
    if missing_statement_ids:
        raise HTTPException(status_code=404, detail=f"银行流水不存在：{','.join(missing_statement_ids)}")

    journal_lines = list_cash_journal_lines(request.account_set_id, request.period)
    journal_by_id = {line["line_id"]: line for line in journal_lines}
    missing_journal_ids = [line_id for line_id in request.journal_line_ids if line_id not in journal_by_id]
    if missing_journal_ids:
        raise HTTPException(status_code=404, detail=f"资金分录行不存在：{','.join(missing_journal_ids)}")

    matched_statement_ids, matched_journal_ids = _matched_line_ids()
    if any(line_id in matched_statement_ids for line_id in request.statement_line_ids):
        raise HTTPException(status_code=409, detail="银行流水已完成对账，不能重复确认。")
    if any(line_id in matched_journal_ids for line_id in request.journal_line_ids):
        raise HTTPException(status_code=409, detail="资金分录行已完成对账，不能重复确认。")

    settlement_ids: list[str] = []
    if request.receivable_payable_settlement is not None:
        settlement = create_counterparty_settlement(request.receivable_payable_settlement)
        settlement_ids.append(settlement.settlement_id)

    match = BankReconciliationMatch(
        reconciliation_id=f"bankrec-{uuid4().hex[:12]}",
        account_set_id=request.account_set_id,
        bank_account_id=request.bank_account_id,
        period=request.period,
        statement_line_ids=request.statement_line_ids,
        journal_line_ids=request.journal_line_ids,
        confirmed_by=request.confirmed_by,
        confirmed_at=_now(),
        note=request.note,
        settlement_ids=settlement_ids,
    )
    _BANK_RECONCILIATION_MATCHES[match.reconciliation_id] = match
    for statement_line_id in request.statement_line_ids:
        _replace_statement_line(statement_by_id[statement_line_id].model_copy(update={"match_status": "matched"}))
    return match


def build_bank_reconciliation_statement(
    account_set_id: str,
    bank_account_id: str,
    period: str,
) -> BankBalanceReconciliationStatement:
    validate_account_set(account_set_id)
    statement_lines = _get_statement_lines(account_set_id, bank_account_id, period)
    journal_lines = list_cash_journal_lines(account_set_id, period)
    matched_statement_ids, matched_journal_ids = _matched_line_ids()
    unmatched_statement_lines = [line for line in statement_lines if line.statement_line_id not in matched_statement_ids]
    unmatched_journal_lines = [line for line in journal_lines if line["line_id"] not in matched_journal_ids]

    bank_balance = _sum_statement_lines(statement_lines)
    book_balance = _sum_journal_lines(journal_lines)
    bank_received_not_booked = _sum_statement_lines(
        [line for line in unmatched_statement_lines if line.direction == "inflow"]
    )
    bank_paid_not_booked = abs(
        _sum_statement_lines([line for line in unmatched_statement_lines if line.direction == "outflow"])
    )
    book_received_not_bank = _sum_journal_lines(
        [line for line in unmatched_journal_lines if line["cash_direction"] == "inflow"]
    )
    book_paid_not_bank = abs(
        _sum_journal_lines([line for line in unmatched_journal_lines if line["cash_direction"] == "outflow"])
    )
    adjusted_bank_balance = bank_balance + book_received_not_bank - book_paid_not_bank
    adjusted_book_balance = book_balance + bank_received_not_booked - bank_paid_not_booked

    return BankBalanceReconciliationStatement(
        account_set_id=account_set_id,
        bank_account_id=bank_account_id,
        period=period,
        bank_balance=bank_balance,
        book_balance=book_balance,
        bank_received_not_booked=bank_received_not_booked,
        bank_paid_not_booked=bank_paid_not_booked,
        book_received_not_bank=book_received_not_bank,
        book_paid_not_bank=book_paid_not_bank,
        adjusted_bank_balance=adjusted_bank_balance,
        adjusted_book_balance=adjusted_book_balance,
        unmatched_statement_count=len(unmatched_statement_lines),
        unmatched_journal_count=len(unmatched_journal_lines),
        unmatched_statement_lines=unmatched_statement_lines,
        unmatched_journal_lines=unmatched_journal_lines,
    )


def _statement_key(line: BankStatementLineCreate) -> str:
    return f"{line.account_set_id}:{line.bank_account_id}:{line.bank_reference}"


def _get_statement_lines(account_set_id: str, bank_account_id: str, period: str) -> list[BankStatementLine]:
    lines = [
        line
        for line in _BANK_STATEMENT_LINES.values()
        if line.account_set_id == account_set_id
        and line.bank_account_id == bank_account_id
        and line.transaction_date[:7] == period
    ]
    lines.sort(key=lambda line: (line.transaction_date, line.bank_reference, line.statement_line_id))
    return lines


def _replace_statement_line(updated: BankStatementLine) -> None:
    for key, line in list(_BANK_STATEMENT_LINES.items()):
        if line.statement_line_id == updated.statement_line_id:
            _BANK_STATEMENT_LINES[key] = updated
            return
    raise HTTPException(status_code=404, detail="银行流水不存在。")


def _matched_line_ids() -> tuple[set[str], set[str]]:
    statement_ids: set[str] = set()
    journal_ids: set[str] = set()
    for match in _BANK_RECONCILIATION_MATCHES.values():
        if match.status != "matched":
            continue
        statement_ids.update(match.statement_line_ids)
        journal_ids.update(match.journal_line_ids)
    return statement_ids, journal_ids


def _sum_statement_lines(lines: list[BankStatementLine]) -> Decimal:
    return sum((_signed_statement_amount(line) for line in lines), ZERO)


def _signed_statement_amount(line: BankStatementLine) -> Decimal:
    return line.amount if line.direction == "inflow" else -line.amount


def _sum_journal_lines(lines: list[dict]) -> Decimal:
    return sum((_signed_journal_amount(line) for line in lines), ZERO)


def _signed_journal_amount(line: dict) -> Decimal:
    return line["base_amount"] if line["cash_direction"] == "inflow" else -line["base_amount"]


def _score_match(statement_line: BankStatementLine, journal_line: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if statement_line.amount == journal_line["base_amount"]:
        score += 60
        reasons.append("金额一致")
    if statement_line.transaction_date == journal_line["entry_date"]:
        score += 25
        reasons.append("日期一致")
    journal_summary = journal_line.get("summary", "")
    if statement_line.summary and statement_line.summary in journal_summary:
        score += 15
        reasons.append("摘要匹配")
    return min(score, 100), reasons


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
