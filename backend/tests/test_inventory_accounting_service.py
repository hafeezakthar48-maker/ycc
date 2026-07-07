from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.inventory_accounting import InventoryMovementCreate
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import list_journal_entries, reset_accounting_store
from app.services.inventory_accounting_service import calculate_moving_average_cost
from app.services.inventory_accounting_service import (
    get_inventory_balance,
    post_purchase_receipt,
    post_sales_issue,
    reset_inventory_accounting_store,
)


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()
    reset_inventory_accounting_store()


def test_inventory_movement_keeps_quantity_and_amount():
    movement = InventoryMovementCreate(
        account_set_id="default",
        sku_id="SKU-001",
        warehouse_id="WH-SH",
        movement_date="2026-06-10",
        movement_type="purchase_receipt",
        quantity=Decimal("10"),
        amount=Decimal("1000.00"),
        source_id="po-001",
    )

    assert movement.quantity == Decimal("10")
    assert movement.amount == Decimal("1000.00")


def test_calculate_moving_average_cost_after_purchase_receipt():
    result = calculate_moving_average_cost(
        existing_quantity=Decimal("10"),
        existing_amount=Decimal("1000.00"),
        receipt_quantity=Decimal("10"),
        receipt_amount=Decimal("1200.00"),
    )

    assert result == Decimal("110.00")


def test_post_purchase_receipt_debits_inventory_and_credits_payable():
    result = post_purchase_receipt(
        account_set_id="default",
        sku_id="SKU-001",
        warehouse_id="WH-SH",
        period="2026-06",
        quantity=Decimal("10"),
        amount=Decimal("1000.00"),
        supplier_id="SUP-001",
        actor_id="inventory-user",
    )
    balance = get_inventory_balance("default", "SKU-001", "WH-SH")
    entries = list_journal_entries("default", "2026-06").entries

    assert result.source_id == "inventory_receipt:default:2026-06:SKU-001:SUP-001"
    assert result.unit_cost == Decimal("100.00")
    assert balance.quantity == Decimal("10.0000")
    assert balance.amount == Decimal("1000.00")
    assert balance.moving_average_cost == Decimal("100.00")
    assert len(entries) == 1
    assert [(line.account_code, line.direction, line.base_amount) for line in entries[0].lines] == [
        ("1405", "debit", Decimal("1000.00")),
        ("2202", "credit", Decimal("1000.00")),
    ]
    assert entries[0].lines[0].dimensions[0].dimension_type == "sku"
    assert entries[0].lines[0].dimensions[1].dimension_type == "warehouse"


def test_post_sales_issue_credits_inventory_and_debits_cogs():
    post_purchase_receipt(
        account_set_id="default",
        sku_id="SKU-001",
        warehouse_id="WH-SH",
        period="2026-06",
        quantity=Decimal("10"),
        amount=Decimal("1000.00"),
        supplier_id="SUP-001",
        actor_id="inventory-user",
    )

    result = post_sales_issue(
        account_set_id="default",
        sku_id="SKU-001",
        warehouse_id="WH-SH",
        period="2026-06",
        quantity=Decimal("3"),
        actor_id="inventory-user",
    )
    balance = get_inventory_balance("default", "SKU-001", "WH-SH")
    entry = next(entry for entry in list_journal_entries("default", "2026-06").entries if entry.source_type == "inventory_sales_issue")

    assert result.cogs_account_code == "6401"
    assert result.journal_entry_id.startswith("je-")
    assert result.cost_amount == Decimal("300.00")
    assert balance.quantity == Decimal("7.0000")
    assert balance.amount == Decimal("700.00")
    assert [(line.account_code, line.direction, line.base_amount) for line in entry.lines] == [
        ("6401", "debit", Decimal("300.00")),
        ("1405", "credit", Decimal("300.00")),
    ]
    assert entry.lines[0].dimensions[0].dimension_type == "sku"
    assert entry.lines[0].dimensions[1].dimension_type == "warehouse"


def test_post_sales_issue_rejects_insufficient_stock():
    post_purchase_receipt(
        account_set_id="default",
        sku_id="SKU-001",
        warehouse_id="WH-SH",
        period="2026-06",
        quantity=Decimal("2"),
        amount=Decimal("200.00"),
        supplier_id="SUP-001",
        actor_id="inventory-user",
    )

    with pytest.raises(HTTPException) as exc_info:
        post_sales_issue(
            account_set_id="default",
            sku_id="SKU-001",
            warehouse_id="WH-SH",
            period="2026-06",
            quantity=Decimal("3"),
            actor_id="inventory-user",
        )

    assert exc_info.value.status_code == 409
