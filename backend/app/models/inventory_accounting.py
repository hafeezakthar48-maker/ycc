from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


InventoryMovementType = Literal[
    "purchase_receipt",
    "sales_issue",
    "sales_return",
    "purchase_return",
    "adjustment_in",
    "adjustment_out",
]


class InventoryMovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    sku_id: str = Field(min_length=1, max_length=64)
    warehouse_id: str = Field(min_length=1, max_length=64)
    movement_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    movement_type: InventoryMovementType
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=4)
    amount: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    source_id: str = Field(min_length=1, max_length=120)


class InventoryMovement(InventoryMovementCreate):
    movement_id: str
    unit_cost: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=4)
    journal_entry_id: str | None = None


class InventoryBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    sku_id: str
    warehouse_id: str
    quantity: Decimal = Field(max_digits=16, decimal_places=4)
    amount: Decimal = Field(max_digits=16, decimal_places=2)
    moving_average_cost: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=4)


class InventorySalesIssueResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    sku_id: str
    warehouse_id: str
    period: str
    movement_id: str
    source_id: str
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=4)
    cost_amount: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    unit_cost: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=4)
    cogs_account_code: str = "6401"
    inventory_account_code: str = "1405"
    journal_entry_id: str
