from decimal import Decimal

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.models.bank_reconciliation import BankStatementLineCreate
from app.services.accounting_service import (
    list_cash_journal_lines,
    post_journal_entry,
    reset_accounting_store,
)
from app.services.bank_reconciliation_service import (
    import_bank_statement_lines,
    reset_bank_reconciliation_store,
    suggest_bank_matches,
)


def setup_function():
    reset_accounting_store()
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


def test_list_cash_journal_lines_reads_bank_deposit_lines():
    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-30",
            source_type="manual",
            source_id="receipt-001",
            description="销售回款入账",
            lines=[
                JournalLineCreate(
                    account_code="1002",
                    account_name="银行存款",
                    direction="debit",
                    original_amount=Decimal("1200.00"),
                    base_amount=Decimal("1200.00"),
                    description="销售回款",
                ),
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="credit",
                    original_amount=Decimal("1200.00"),
                    base_amount=Decimal("1200.00"),
                    description="销售回款",
                ),
            ],
        )
    )

    lines = list_cash_journal_lines("default", "2026-06")

    assert len(lines) == 1
    assert lines[0]["entry_id"] == entry.id
    assert lines[0]["line_id"] == entry.lines[0].id
    assert lines[0]["cash_direction"] == "inflow"
    assert lines[0]["base_amount"] == Decimal("1200.00")


def test_suggest_bank_matches_scores_amount_date_and_summary():
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-30",
            source_type="manual",
            source_id="receipt-002",
            description="销售回款入账",
            lines=[
                JournalLineCreate(
                    account_code="1002",
                    account_name="银行存款",
                    direction="debit",
                    original_amount=Decimal("1200.00"),
                    base_amount=Decimal("1200.00"),
                    description="销售回款",
                ),
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="credit",
                    original_amount=Decimal("1200.00"),
                    base_amount=Decimal("1200.00"),
                    description="销售回款",
                ),
            ],
        )
    )
    imported = import_bank_statement_lines("default", [_bank_line()])

    result = suggest_bank_matches(
        account_set_id="default",
        bank_account_id="bank-001",
        period="2026-06",
        minimum_score=80,
    )

    assert result.period == "2026-06"
    assert result.candidates[0].statement_line_id == imported.lines[0].statement_line_id
    assert result.candidates[0].score == 100
