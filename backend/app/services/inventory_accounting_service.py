from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException

from app.models.accounting import AuxiliaryDimensionCreate, JournalEntryCreate, JournalLineCreate, JournalLineDimension
from app.models.inventory_accounting import InventoryBalance, InventoryMovement
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.accounting_service import get_chart_of_accounts, post_journal_entry, upsert_auxiliary_dimension


MONEY_QUANT = Decimal("0.01")
QUANTITY_QUANT = Decimal("0.0001")
_INVENTORY_BALANCES: dict[tuple[str, str, str], InventoryBalance] = {}
_INVENTORY_MOVEMENTS: list[InventoryMovement] = []


def reset_inventory_accounting_store() -> None:
    _INVENTORY_BALANCES.clear()
    _INVENTORY_MOVEMENTS.clear()


def get_inventory_balance(account_set_id: str, sku_id: str, warehouse_id: str) -> InventoryBalance:
    validate_account_set(account_set_id)
    key = _balance_key(account_set_id, sku_id, warehouse_id)
    return _INVENTORY_BALANCES.get(
        key,
        InventoryBalance(
            account_set_id=account_set_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            quantity=Decimal("0.0000"),
            amount=Decimal("0.00"),
            moving_average_cost=Decimal("0.00"),
        ),
    )


def post_purchase_receipt(
    account_set_id: str,
    sku_id: str,
    warehouse_id: str,
    period: str,
    quantity: Decimal,
    amount: Decimal,
    supplier_id: str,
    actor_id: str,
) -> InventoryMovement:
    _validate_period_open(account_set_id, period)
    quantity = _quantity(quantity)
    amount = _money(amount)
    if quantity <= Decimal("0.0000"):
        raise HTTPException(status_code=422, detail="入库数量必须大于 0。")
    if amount <= Decimal("0.00"):
        raise HTTPException(status_code=422, detail="入库金额必须大于 0。")

    source_type = "inventory_receipt"
    source_id = f"{source_type}:{account_set_id}:{period}:{sku_id}:{supplier_id}"
    existing = _movement_by_source(source_id)
    if existing is not None:
        return existing

    _ensure_dimensions(account_set_id, sku_id, warehouse_id, supplier_id)
    balance = get_inventory_balance(account_set_id, sku_id, warehouse_id)
    moving_average_cost = calculate_moving_average_cost(balance.quantity, balance.amount, quantity, amount)
    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} {sku_id} 采购入库",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=build_purchase_receipt_lines(account_set_id, amount, sku_id, warehouse_id, supplier_id),
        )
    )
    movement = InventoryMovement(
        movement_id=f"im-{uuid4().hex[:12]}",
        account_set_id=account_set_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        movement_date=_period_end_date(period),
        movement_type="purchase_receipt",
        quantity=quantity,
        amount=amount,
        source_id=source_id,
        unit_cost=moving_average_cost,
        journal_entry_id=entry.id,
    )
    _INVENTORY_MOVEMENTS.append(movement)
    _INVENTORY_BALANCES[_balance_key(account_set_id, sku_id, warehouse_id)] = InventoryBalance(
        account_set_id=account_set_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        quantity=_quantity(balance.quantity + quantity),
        amount=_money(balance.amount + amount),
        moving_average_cost=moving_average_cost,
    )
    return movement


def build_purchase_receipt_lines(
    account_set_id: str,
    amount: Decimal,
    sku_id: str,
    warehouse_id: str,
    supplier_id: str,
) -> list[JournalLineCreate]:
    account_names = _account_names(account_set_id)
    return [
        JournalLineCreate(
            account_code="1405",
            account_name=account_names.get("1405", "库存商品"),
            direction="debit",
            original_amount=_money(amount),
            base_amount=_money(amount),
            description=f"{sku_id} 采购入库",
            dimensions=[
                JournalLineDimension(dimension_type="sku", dimension_code=sku_id),
                JournalLineDimension(dimension_type="warehouse", dimension_code=warehouse_id),
            ],
        ),
        JournalLineCreate(
            account_code="2202",
            account_name=account_names.get("2202", "应付账款"),
            direction="credit",
            original_amount=_money(amount),
            base_amount=_money(amount),
            description=f"{supplier_id} 采购挂账",
            dimensions=[JournalLineDimension(dimension_type="supplier", dimension_code=supplier_id)],
        ),
    ]


def calculate_moving_average_cost(
    existing_quantity: Decimal,
    existing_amount: Decimal,
    receipt_quantity: Decimal,
    receipt_amount: Decimal,
) -> Decimal:
    total_quantity = Decimal(existing_quantity) + Decimal(receipt_quantity)
    if total_quantity <= Decimal("0"):
        return Decimal("0.00")
    return _money((Decimal(existing_amount) + Decimal(receipt_amount)) / total_quantity)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _quantity(value: Decimal) -> Decimal:
    return Decimal(value).quantize(QUANTITY_QUANT, rounding=ROUND_HALF_UP)


def _balance_key(account_set_id: str, sku_id: str, warehouse_id: str) -> tuple[str, str, str]:
    return (account_set_id, sku_id, warehouse_id)


def _validate_period_open(account_set_id: str, period: str) -> None:
    validate_account_set(account_set_id)
    if is_accounting_period_closed(period, account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能生成存货正式分录。")


def _ensure_dimensions(account_set_id: str, sku_id: str, warehouse_id: str, supplier_id: str | None = None) -> None:
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id=account_set_id,
            dimension_type="sku",
            dimension_code=sku_id,
            dimension_name=sku_id,
        )
    )
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id=account_set_id,
            dimension_type="warehouse",
            dimension_code=warehouse_id,
            dimension_name=warehouse_id,
        )
    )
    if supplier_id is not None:
        upsert_auxiliary_dimension(
            AuxiliaryDimensionCreate(
                account_set_id=account_set_id,
                dimension_type="supplier",
                dimension_code=supplier_id,
                dimension_name=supplier_id,
            )
        )


def _movement_by_source(source_id: str) -> InventoryMovement | None:
    return next((movement for movement in _INVENTORY_MOVEMENTS if movement.source_id == source_id), None)


def _account_names(account_set_id: str) -> dict[str, str]:
    return {account.account_code: account.account_name for account in get_chart_of_accounts(account_set_id).accounts}


def _period_end_date(period: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    return f"{period}-{monthrange(year, month)[1]:02d}"
