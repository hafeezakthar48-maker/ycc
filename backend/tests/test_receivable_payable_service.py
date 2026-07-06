from decimal import Decimal

from app.models.accounting import (
    AuxiliaryDimensionCreate,
    JournalEntryCreate,
    JournalLineCreate,
    JournalLineDimension,
)
from app.models.receivable_payable import CounterpartySettlementCreate, CounterpartySettlementItemCreate
from app.services.accounting_service import (
    list_counterparty_journal_lines,
    post_journal_entry,
    reset_accounting_store,
    upsert_auxiliary_dimension,
)
from app.services.receivable_payable_service import (
    build_aging_report,
    build_counterparty_balances,
    build_counterparty_open_items,
    create_counterparty_settlement,
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


def test_build_aging_report_places_open_items_into_buckets():
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-04-01",
            source_type="voucher_center",
            source_id="voucher-ar-aging-001",
            description="确认客户应收",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("1000.00"),
                    base_amount=Decimal("1000.00"),
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
            ],
        )
    )

    report = build_aging_report("default", "2026-06", "receivable", as_of_date="2026-06-30")

    bucket_by_code = {bucket.bucket_code: bucket.amount for bucket in report.buckets}
    assert bucket_by_code["61-90"] == Decimal("1000.00")
    assert report.total_base_balance == Decimal("1000.00")


def test_create_partial_receivable_settlement_reduces_open_amount():
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-05",
            source_type="voucher_center",
            source_id="voucher-ar-settle-001",
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
    open_item = build_counterparty_open_items("default", "2026-06", "receivable")[0]

    settlement = create_counterparty_settlement(
        CounterpartySettlementCreate(
            account_set_id="default",
            period="2026-06",
            open_item_type="receivable",
            settlement_date="2026-06-20",
            counterparty_type="customer",
            counterparty_code="CUST-SH-001",
            payment_entry_id="bank-receipt-001",
            items=[
                CounterpartySettlementItemCreate(
                    open_item_id=open_item.open_item_id,
                    source_line_id=open_item.source_line_id,
                    settled_base_amount=Decimal("600.00"),
                )
            ],
            settled_by="finance-user",
        )
    )
    items_after = build_counterparty_open_items("default", "2026-06", "receivable")

    assert settlement.total_settled_base_amount == Decimal("600.00")
    assert items_after[0].open_base_amount == Decimal("460.00")
    assert items_after[0].status == "partial"
