from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.accounting import AuxiliaryDimensionCreate, JournalEntryCreate, JournalLineCreate, JournalLineDimension
from app.services.accounting_service import (
    get_auxiliary_dimension,
    get_journal_entry,
    list_auxiliary_dimensions,
    post_journal_entry,
    reset_accounting_store,
    upsert_auxiliary_dimension,
)


def setup_function():
    reset_accounting_store()


def test_upsert_and_list_customer_dimension():
    created = upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-SH-001",
            dimension_name="上海云智科技有限公司",
        )
    )

    loaded = get_auxiliary_dimension("default", "customer", "CUST-SH-001")
    listed = list_auxiliary_dimensions("default", "customer")

    assert created.dimension_name == "上海云智科技有限公司"
    assert loaded.dimension_code == "CUST-SH-001"
    assert listed.total == 1
    assert listed.dimensions[0].dimension_type == "customer"


def test_list_dimension_types_contains_core_finance_dimensions():
    dimensions = list_auxiliary_dimensions("default").supported_dimension_types

    assert "customer" in dimensions
    assert "supplier" in dimensions
    assert "department" in dimensions
    assert "asset" in dimensions
    assert "sku" in dimensions


def _seed_customer():
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-SH-001",
            dimension_name="上海云智科技有限公司",
        )
    )


def test_post_journal_entry_persists_line_dimensions():
    _seed_customer()

    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="dimension-entry-1",
            description="客户维度收入",
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

    loaded = get_journal_entry(entry.id)
    assert loaded.lines[0].dimensions[0].dimension_type == "customer"
    assert loaded.lines[0].dimensions[0].dimension_code == "CUST-SH-001"
    assert loaded.lines[0].dimensions[0].dimension_name == "上海云智科技有限公司"


def test_post_journal_entry_rejects_missing_dimension_master_data():
    request = JournalEntryCreate(
        account_set_id="default",
        entry_date="2026-06-18",
        source_type="manual_adjustment",
        source_id="dimension-entry-missing",
        description="缺少客户维度",
        lines=[
            JournalLineCreate(
                account_code="1122",
                account_name="应收账款",
                direction="debit",
                original_amount=Decimal("1000.00"),
                base_amount=Decimal("1000.00"),
                dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-MISSING")],
            ),
            JournalLineCreate(
                account_code="6001",
                account_name="主营业务收入",
                direction="credit",
                original_amount=Decimal("1000.00"),
                base_amount=Decimal("1000.00"),
                dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-MISSING")],
            ),
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        post_journal_entry(request)

    assert exc_info.value.status_code == 422
    assert "辅助核算维度不存在" in exc_info.value.detail


def test_list_journal_entries_by_dimension_returns_matching_entries_only():
    from app.services.accounting_service import list_journal_entries_by_dimension

    _seed_customer()
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-BJ-002",
            dimension_name="北京客户",
        )
    )

    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="dimension-filter-1",
            description="上海客户收入",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("100.00"),
                    base_amount=Decimal("100.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("100.00"),
                    base_amount=Decimal("100.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
            ],
        )
    )
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-19",
            source_type="manual_adjustment",
            source_id="dimension-filter-2",
            description="北京客户收入",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("200.00"),
                    base_amount=Decimal("200.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-BJ-002")],
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("200.00"),
                    base_amount=Decimal("200.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-BJ-002")],
                ),
            ],
        )
    )

    result = list_journal_entries_by_dimension("default", "2026-06", "customer", "CUST-SH-001")

    assert result.total == 1
    assert result.entries[0].source_id == "dimension-filter-1"
