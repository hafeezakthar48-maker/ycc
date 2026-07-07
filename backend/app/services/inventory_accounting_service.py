from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException

from app.models.accounting import AuxiliaryDimensionCreate, JournalEntryCreate, JournalLineCreate, JournalLineDimension
from app.models.inventory_accounting import (
    InventoryBalance,
    InventoryCountVarianceResult,
    InventoryMovement,
    InventorySalesIssueResult,
)
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.accounting_service import (
    get_chart_of_accounts,
    list_journal_entries,
    post_journal_entry,
    upsert_auxiliary_dimension,
)


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


def list_inventory_balances(account_set_id: str = "default") -> list[InventoryBalance]:
    validate_account_set(account_set_id)
    balances = [balance for balance in _INVENTORY_BALANCES.values() if balance.account_set_id == account_set_id]
    balances.sort(key=lambda item: (item.sku_id, item.warehouse_id))
    return balances


def list_inventory_movements(account_set_id: str = "default") -> list[InventoryMovement]:
    validate_account_set(account_set_id)
    movements = [movement for movement in _INVENTORY_MOVEMENTS if movement.account_set_id == account_set_id]
    movements.sort(key=lambda item: (item.movement_date, item.sku_id, item.warehouse_id, item.movement_id))
    return movements


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


def post_sales_issue(
    account_set_id: str,
    sku_id: str,
    warehouse_id: str,
    period: str,
    quantity: Decimal,
    actor_id: str,
) -> InventorySalesIssueResult:
    _validate_period_open(account_set_id, period)
    quantity = _quantity(quantity)
    if quantity <= Decimal("0.0000"):
        raise HTTPException(status_code=422, detail="出库数量必须大于 0。")

    _ensure_dimensions(account_set_id, sku_id, warehouse_id)
    balance = get_inventory_balance(account_set_id, sku_id, warehouse_id)
    ensure_available_stock(balance, quantity)
    unit_cost = _money(balance.moving_average_cost)
    cost_amount = _money(quantity * unit_cost)
    if quantity == balance.quantity:
        remaining_amount = Decimal("0.00")
        remaining_cost = Decimal("0.00")
    else:
        remaining_amount = _money(balance.amount - cost_amount)
        if remaining_amount < Decimal("0.00"):
            raise HTTPException(status_code=409, detail="出库成本会导致库存金额为负，不能结转销售成本。")
        remaining_cost = calculate_moving_average_cost(
            existing_quantity=Decimal("0.0000"),
            existing_amount=Decimal("0.00"),
            receipt_quantity=balance.quantity - quantity,
            receipt_amount=remaining_amount,
        )

    source_type = "inventory_sales_issue"
    source_id = f"{source_type}:{account_set_id}:{period}:{sku_id}:{warehouse_id}:{len(_INVENTORY_MOVEMENTS) + 1}"
    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} {sku_id} 销售出库成本结转",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=build_sales_issue_lines(account_set_id, cost_amount, sku_id, warehouse_id),
        )
    )
    movement = InventoryMovement(
        movement_id=f"im-{uuid4().hex[:12]}",
        account_set_id=account_set_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        movement_date=_period_end_date(period),
        movement_type="sales_issue",
        quantity=quantity,
        amount=cost_amount,
        source_id=source_id,
        unit_cost=unit_cost,
        journal_entry_id=entry.id,
    )
    _INVENTORY_MOVEMENTS.append(movement)
    _INVENTORY_BALANCES[_balance_key(account_set_id, sku_id, warehouse_id)] = InventoryBalance(
        account_set_id=account_set_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        quantity=_quantity(balance.quantity - quantity),
        amount=remaining_amount,
        moving_average_cost=remaining_cost,
    )
    return InventorySalesIssueResult(
        account_set_id=account_set_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        period=period,
        movement_id=movement.movement_id,
        source_id=source_id,
        quantity=quantity,
        cost_amount=cost_amount,
        unit_cost=unit_cost,
        journal_entry_id=entry.id,
    )


def ensure_available_stock(balance: InventoryBalance, issue_quantity: Decimal) -> None:
    if balance.quantity < issue_quantity:
        raise HTTPException(status_code=409, detail="库存数量不足，不能结转销售成本。")


def record_inventory_impairment(
    account_set_id: str,
    sku_id: str,
    period: str,
    amount: Decimal,
    actor_id: str,
):
    _validate_period_open(account_set_id, period)
    amount = _money(amount)
    if amount <= Decimal("0.00"):
        raise HTTPException(status_code=422, detail="跌价准备金额必须大于 0。")
    source_type = "inventory_impairment"
    source_id = f"{source_type}:{account_set_id}:{period}:{sku_id}"
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing is not None:
        return existing

    _ensure_sku_dimension(account_set_id, sku_id)
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} {sku_id} 存货跌价准备",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=build_inventory_impairment_lines(account_set_id, amount, sku_id),
        )
    )


def record_inventory_count_variance(
    account_set_id: str,
    sku_id: str,
    warehouse_id: str,
    period: str,
    actual_quantity: Decimal,
    actor_id: str,
    approved_by: str,
    approved_at: str,
) -> InventoryCountVarianceResult:
    _validate_period_open(account_set_id, period)
    actual_quantity = _quantity(actual_quantity)
    if actual_quantity < Decimal("0.0000"):
        raise HTTPException(status_code=422, detail="盘点实盘数量不能小于 0。")
    if not approved_by or not approved_at:
        raise HTTPException(status_code=422, detail="盘点差异必须保留审批人和审批时间。")

    _ensure_dimensions(account_set_id, sku_id, warehouse_id)
    balance = get_inventory_balance(account_set_id, sku_id, warehouse_id)
    variance_quantity = _quantity(actual_quantity - balance.quantity)
    variance_type = "gain" if variance_quantity > Decimal("0.0000") else "loss" if variance_quantity < Decimal("0.0000") else "none"
    source_type = "inventory_count_variance"
    source_id = f"{source_type}:{account_set_id}:{period}:{sku_id}:{warehouse_id}"
    if variance_type == "none":
        return InventoryCountVarianceResult(
            account_set_id=account_set_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            period=period,
            variance_type="none",
            book_quantity=balance.quantity,
            actual_quantity=actual_quantity,
            variance_quantity=Decimal("0.0000"),
            variance_amount=Decimal("0.00"),
            source_id=source_id,
            approved_by=approved_by,
            approved_at=approved_at,
        )

    unit_cost = _money(balance.moving_average_cost)
    variance_amount = _money(abs(variance_quantity) * unit_cost)
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing is not None:
        return InventoryCountVarianceResult(
            account_set_id=account_set_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            period=period,
            variance_type=variance_type,
            book_quantity=balance.quantity,
            actual_quantity=actual_quantity,
            variance_quantity=variance_quantity,
            variance_amount=variance_amount,
            source_id=source_id,
            approved_by=approved_by,
            approved_at=approved_at,
            journal_entry_id=existing.id,
        )

    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} {sku_id} 盘点差异，审批人：{approved_by}，审批时间：{approved_at}",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=build_inventory_count_variance_lines(
                account_set_id=account_set_id,
                variance_type=variance_type,
                variance_amount=variance_amount,
                sku_id=sku_id,
                warehouse_id=warehouse_id,
            ),
        )
    )
    movement = InventoryMovement(
        movement_id=f"im-{uuid4().hex[:12]}",
        account_set_id=account_set_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        movement_date=_period_end_date(period),
        movement_type="adjustment_in" if variance_type == "gain" else "adjustment_out",
        quantity=abs(variance_quantity),
        amount=variance_amount,
        source_id=source_id,
        unit_cost=unit_cost,
        journal_entry_id=entry.id,
    )
    _INVENTORY_MOVEMENTS.append(movement)
    new_amount = _money(balance.amount + variance_amount) if variance_type == "gain" else _money(balance.amount - variance_amount)
    if new_amount < Decimal("0.00"):
        raise HTTPException(status_code=409, detail="盘点差异会导致库存金额为负，不能入账。")
    _INVENTORY_BALANCES[_balance_key(account_set_id, sku_id, warehouse_id)] = InventoryBalance(
        account_set_id=account_set_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        quantity=actual_quantity,
        amount=new_amount,
        moving_average_cost=calculate_moving_average_cost(
            existing_quantity=Decimal("0.0000"),
            existing_amount=Decimal("0.00"),
            receipt_quantity=actual_quantity,
            receipt_amount=new_amount,
        ),
    )
    return InventoryCountVarianceResult(
        account_set_id=account_set_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        period=period,
        variance_type=variance_type,
        book_quantity=balance.quantity,
        actual_quantity=actual_quantity,
        variance_quantity=variance_quantity,
        variance_amount=variance_amount,
        source_id=source_id,
        approved_by=approved_by,
        approved_at=approved_at,
        journal_entry_id=entry.id,
    )


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


def build_sales_issue_lines(
    account_set_id: str,
    cost_amount: Decimal,
    sku_id: str,
    warehouse_id: str,
) -> list[JournalLineCreate]:
    account_names = _account_names(account_set_id)
    return [
        JournalLineCreate(
            account_code="6401",
            account_name=account_names.get("6401", "主营业务成本"),
            direction="debit",
            original_amount=_money(cost_amount),
            base_amount=_money(cost_amount),
            description=f"{sku_id} 销售成本结转",
            dimensions=[
                JournalLineDimension(dimension_type="sku", dimension_code=sku_id),
                JournalLineDimension(dimension_type="warehouse", dimension_code=warehouse_id),
            ],
        ),
        JournalLineCreate(
            account_code="1405",
            account_name=account_names.get("1405", "库存商品"),
            direction="credit",
            original_amount=_money(cost_amount),
            base_amount=_money(cost_amount),
            description=f"{sku_id} 销售出库",
            dimensions=[
                JournalLineDimension(dimension_type="sku", dimension_code=sku_id),
                JournalLineDimension(dimension_type="warehouse", dimension_code=warehouse_id),
            ],
        ),
    ]


def build_inventory_impairment_lines(
    account_set_id: str,
    amount: Decimal,
    sku_id: str,
) -> list[JournalLineCreate]:
    account_names = _account_names(account_set_id)
    dimensions = [JournalLineDimension(dimension_type="sku", dimension_code=sku_id)]
    return [
        JournalLineCreate(
            account_code="6701",
            account_name=account_names.get("6701", "资产减值损失"),
            direction="debit",
            original_amount=_money(amount),
            base_amount=_money(amount),
            description=f"{sku_id} 存货跌价损失",
            dimensions=dimensions,
        ),
        JournalLineCreate(
            account_code="1471",
            account_name=account_names.get("1471", "存货跌价准备"),
            direction="credit",
            original_amount=_money(amount),
            base_amount=_money(amount),
            description=f"{sku_id} 存货跌价准备",
            dimensions=dimensions,
        ),
    ]


def build_inventory_count_variance_lines(
    account_set_id: str,
    variance_type: str,
    variance_amount: Decimal,
    sku_id: str,
    warehouse_id: str,
) -> list[JournalLineCreate]:
    account_names = _account_names(account_set_id)
    dimensions = [
        JournalLineDimension(dimension_type="sku", dimension_code=sku_id),
        JournalLineDimension(dimension_type="warehouse", dimension_code=warehouse_id),
    ]
    inventory_line = JournalLineCreate(
        account_code="1405",
        account_name=account_names.get("1405", "库存商品"),
        direction="debit" if variance_type == "gain" else "credit",
        original_amount=_money(variance_amount),
        base_amount=_money(variance_amount),
        description=f"{sku_id} 盘点{'盘盈' if variance_type == 'gain' else '盘亏'}",
        dimensions=dimensions,
    )
    pending_line = JournalLineCreate(
        account_code="1901",
        account_name=account_names.get("1901", "待处理财产损溢"),
        direction="credit" if variance_type == "gain" else "debit",
        original_amount=_money(variance_amount),
        base_amount=_money(variance_amount),
        description=f"{sku_id} 盘点差异待处理",
        dimensions=dimensions,
    )
    return [inventory_line, pending_line] if variance_type == "gain" else [pending_line, inventory_line]


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
    _ensure_sku_dimension(account_set_id, sku_id)
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


def _ensure_sku_dimension(account_set_id: str, sku_id: str) -> None:
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id=account_set_id,
            dimension_type="sku",
            dimension_code=sku_id,
            dimension_name=sku_id,
        )
    )


def _movement_by_source(source_id: str) -> InventoryMovement | None:
    return next((movement for movement in _INVENTORY_MOVEMENTS if movement.source_id == source_id), None)


def _existing_entry(account_set_id: str, period: str, source_type: str, source_id: str):
    return next(
        (
            entry
            for entry in list_journal_entries(account_set_id, period).entries
            if entry.status == "posted" and entry.source_type == source_type and entry.source_id == source_id
        ),
        None,
    )


def _account_names(account_set_id: str) -> dict[str, str]:
    return {account.account_code: account.account_name for account in get_chart_of_accounts(account_set_id).accounts}


def _period_end_date(period: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    return f"{period}-{monthrange(year, month)[1]:02d}"
