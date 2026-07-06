from datetime import UTC, datetime
from uuid import uuid4

from app.models.bank_reconciliation import (
    BankStatementImportResult,
    BankStatementLine,
    BankStatementLineCreate,
)
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


def _statement_key(line: BankStatementLineCreate) -> str:
    return f"{line.account_set_id}:{line.bank_account_id}:{line.bank_reference}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
