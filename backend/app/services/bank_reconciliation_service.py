from datetime import UTC, datetime
from uuid import uuid4

from app.models.bank_reconciliation import (
    BankMatchCandidate,
    BankMatchCandidateResponse,
    BankStatementImportResult,
    BankStatementLine,
    BankStatementLineCreate,
)
from app.services.accounting_service import list_cash_journal_lines
from app.services.accounting_period_service import validate_account_set


_BANK_STATEMENT_LINES: dict[str, BankStatementLine] = {}


def reset_bank_reconciliation_store() -> None:
    _BANK_STATEMENT_LINES.clear()


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


def _statement_key(line: BankStatementLineCreate) -> str:
    return f"{line.account_set_id}:{line.bank_account_id}:{line.bank_reference}"


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
