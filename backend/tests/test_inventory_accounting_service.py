from decimal import Decimal

from app.models.inventory_accounting import InventoryMovementCreate


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
