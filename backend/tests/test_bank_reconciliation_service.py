from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.models.accounting import AuxiliaryDimensionCreate, JournalLineDimension
from app.models.bank_reconciliation import BankReconciliationConfirmRequest, BankStatementLineCreate
from app.models.receivable_payable import CounterpartySettlementCreate, CounterpartySettlementItemCreate
from app.services.accounting_period_service import close_accounting_period, reset_accounting_period_store
from app.services.accounting_service import (
    list_cash_journal_lines,
    post_journal_entry,
    reset_accounting_store,
    upsert_auxiliary_dimension,
)
from app.services.bank_reconciliation_service import (
    build_bank_reconciliation_statement,
    confirm_bank_reconciliation,
    import_bank_statement_lines,
    reset_bank_reconciliation_store,
    suggest_bank_matches,
)
from app.services.receivable_payable_service import (
    build_counterparty_open_items,
    reset_receivable_payable_store,
)
from app.services.voucher_center_service import reset_voucher_store


def setup_function():
    reset_voucher_store()
    reset_accounting_store()
    reset_accounting_period_store()
    reset_bank_reconciliation_store()
    reset_receivable_payable_store()


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
    _post_bank_receipt("receipt-002")
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


def test_confirm_reconciliation_appears_in_balance_statement():
    _post_bank_receipt("receipt-003")
    imported = import_bank_statement_lines("default", [_bank_line()])
    candidate = suggest_bank_matches("default", "bank-001", "2026-06").candidates[0]

    confirmed = confirm_bank_reconciliation(
        BankReconciliationConfirmRequest(
            account_set_id="default",
            bank_account_id="bank-001",
            period="2026-06",
            statement_line_ids=[imported.lines[0].statement_line_id],
            journal_line_ids=[candidate.journal_line_id],
            confirmed_by="treasury-user",
        )
    )
    statement = build_bank_reconciliation_statement("default", "bank-001", "2026-06")

    assert confirmed.status == "matched"
    assert statement.bank_balance == Decimal("1200.00")
    assert statement.book_balance == Decimal("1200.00")
    assert statement.adjusted_bank_balance == statement.adjusted_book_balance
    assert statement.unmatched_statement_count == 0
    assert statement.unmatched_journal_count == 0


def test_confirm_reconciliation_rejects_closed_period():
    _post_bank_receipt("receipt-004")
    imported = import_bank_statement_lines("default", [_bank_line()])
    candidate = suggest_bank_matches("default", "bank-001", "2026-06").candidates[0]
    close_accounting_period("2026-06", "财务主管")

    with pytest.raises(HTTPException) as exc_info:
        confirm_bank_reconciliation(
            BankReconciliationConfirmRequest(
                account_set_id="default",
                bank_account_id="bank-001",
                period="2026-06",
                statement_line_ids=[imported.lines[0].statement_line_id],
                journal_line_ids=[candidate.journal_line_id],
                confirmed_by="treasury-user",
            )
        )

    assert exc_info.value.status_code == 409


def test_confirm_reconciliation_can_create_receivable_settlement():
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-SH-001",
            dimension_name="上海客户A",
        )
    )
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-01",
            source_type="manual",
            source_id="ar-001",
            description="确认应收账款",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("1200.00"),
                    base_amount=Decimal("1200.00"),
                    description="确认应收",
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("1200.00"),
                    base_amount=Decimal("1200.00"),
                    description="确认收入",
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
            ],
        )
    )
    _post_bank_receipt("receipt-005")
    open_item = build_counterparty_open_items("default", "2026-06", "receivable")[0]
    imported = import_bank_statement_lines("default", [_bank_line()])
    candidate = suggest_bank_matches("default", "bank-001", "2026-06").candidates[0]

    confirmed = confirm_bank_reconciliation(
        BankReconciliationConfirmRequest(
            account_set_id="default",
            bank_account_id="bank-001",
            period="2026-06",
            statement_line_ids=[imported.lines[0].statement_line_id],
            journal_line_ids=[candidate.journal_line_id],
            confirmed_by="treasury-user",
            receivable_payable_settlement=CounterpartySettlementCreate(
                account_set_id="default",
                period="2026-06",
                open_item_type="receivable",
                settlement_date="2026-06-30",
                counterparty_type="customer",
                counterparty_code="CUST-SH-001",
                payment_entry_id="bank-receipt-005",
                items=[
                    CounterpartySettlementItemCreate(
                        open_item_id=open_item.open_item_id,
                        source_line_id=open_item.source_line_id,
                        settled_base_amount=Decimal("1200.00"),
                    )
                ],
                settled_by="treasury-user",
            ),
        )
    )
    items_after = build_counterparty_open_items("default", "2026-06", "receivable")

    assert len(confirmed.settlement_ids) == 1
    assert items_after[0].open_base_amount == Decimal("0.00")
    assert items_after[0].status == "settled"


def _post_bank_receipt(source_id: str):
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-30",
            source_type="manual",
            source_id=source_id,
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
