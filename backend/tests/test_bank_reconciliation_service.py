from decimal import Decimal

from app.models.bank_reconciliation import BankStatementLineCreate
from app.services.bank_reconciliation_service import (
    import_bank_statement_lines,
    reset_bank_reconciliation_store,
)


def setup_function():
    reset_bank_reconciliation_store()


def _bank_line(reference: str = "B20260630001") -> BankStatementLineCreate:
    return BankStatementLineCreate(
        account_set_id="default",
        bank_account_id="bank-001",
        transaction_date="2026-06-30",
        direction="inflow",
        amount=Decimal("1200.00"),
        currency="CNY",
        counterparty_name="上海客户A",
        summary="销售回款",
        bank_reference=reference,
    )


def test_bank_statement_line_requires_positive_amount():
    line = _bank_line()

    assert line.amount == Decimal("1200.00")
    assert line.direction == "inflow"


def test_import_bank_statement_lines_deduplicates_by_bank_reference():
    line = _bank_line()

    result = import_bank_statement_lines("default", [line, line])

    assert result.imported_count == 1
    assert result.duplicate_count == 1
    assert result.lines[0].match_status == "unmatched"
