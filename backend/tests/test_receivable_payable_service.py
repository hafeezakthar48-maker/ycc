from decimal import Decimal

from app.models.accounting import (
    AuxiliaryDimensionCreate,
    JournalEntryCreate,
    JournalLineCreate,
    JournalLineDimension,
)
from app.services.accounting_service import (
    list_counterparty_journal_lines,
    post_journal_entry,
    reset_accounting_store,
    upsert_auxiliary_dimension,
)
from app.services.receivable_payable_service import (
    build_counterparty_balances,
    build_counterparty_open_items,
    reset_receivable_payable_store,
)


def setup_function():
    reset_accounting_store()
    reset_receivable_payable_store()


def _seed_customer():
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-SH-001",
            dimension_name="上海客户",
        )
    )


def test_list_counterparty_journal_lines_reads_customer_ar_lines():
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-05",
            source_type="voucher_center",
            source_id="voucher-ar-001",
            description="确认客户应收",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("1060.00"),
                    base_amount=Decimal("1060.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("1000.00"),
                    base_amount=Decimal("1000.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
                JournalLineCreate(
                    account_code="2221",
                    account_name="应交税费",
                    direction="credit",
                    original_amount=Decimal("60.00"),
                    base_amount=Decimal("60.00"),
                ),
            ],
        )
    )

    lines = list_counterparty_journal_lines(
        account_set_id="default",
        period_to="2026-06",
        account_prefixes=["1122"],
        dimension_type="customer",
    )

    assert len(lines) == 1
    assert lines[0]["account_code"] == "1122"
    assert lines[0]["counterparty_code"] == "CUST-SH-001"
    assert lines[0]["counterparty_name"] == "上海客户"


def test_build_receivable_open_items_from_formal_ar_lines():
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-05",
            source_type="voucher_center",
            source_id="voucher-ar-open-001",
            description="确认客户应收",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("1060.00"),
                    base_amount=Decimal("1060.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("1000.00"),
                    base_amount=Decimal("1000.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
                JournalLineCreate(
                    account_code="2221",
                    account_name="应交税费",
                    direction="credit",
                    original_amount=Decimal("60.00"),
                    base_amount=Decimal("60.00"),
                ),
            ],
        )
    )

    items = build_counterparty_open_items("default", "2026-06", "receivable")
    balances = build_counterparty_balances("default", "2026-06", "receivable")

    assert len(items) == 1
    assert items[0].counterparty_code == "CUST-SH-001"
    assert items[0].open_base_amount == Decimal("1060.00")
    assert balances.total_base_balance == Decimal("1060.00")
    assert balances.items[0].open_item_count == 1
