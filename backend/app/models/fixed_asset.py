from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
PERIOD_PATTERN = r"^\d{4}-\d{2}$"

FixedAssetStatus = Literal["active", "disposed", "sold"]
DepreciationMethod = Literal["straight_line"]
InventoryStatus = Literal["unchecked", "checked"]


class FixedAssetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    acquisition_date: str = Field(pattern=DATE_PATTERN)
    original_cost: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    salvage_value: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    useful_life_months: int = Field(ge=1, le=600)
    depreciation_method: DepreciationMethod = "straight_line"
    location: str = Field(default="", max_length=120)
    custodian: str = Field(default="", max_length=80)

    @model_validator(mode="after")
    def validate_salvage_value(self):
        if self.salvage_value >= self.original_cost:
            raise ValueError("残值必须小于资产原值。")
        return self


class FixedAssetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    account_set_id: str
    asset_code: str
    name: str
    category: str
    acquisition_date: str
    original_cost: Decimal
    salvage_value: Decimal
    useful_life_months: int
    depreciation_method: DepreciationMethod
    monthly_depreciation: Decimal
    accumulated_depreciation: Decimal
    net_book_value: Decimal
    status: FixedAssetStatus
    location: str
    custodian: str
    condition: str = "正常"
    inventory_status: InventoryStatus = "unchecked"
    last_inventory_date: str | None = None
    last_inventory_by: str | None = None
    inventory_note: str | None = None
    last_depreciated_period: str | None = None
    disposal_date: str | None = None
    disposal_reason: str | None = None
    disposed_by: str | None = None
    sale_date: str | None = None
    sale_amount: Decimal | None = None
    sale_gain_or_loss: Decimal | None = None
    sale_reason: str | None = None
    sold_by: str | None = None
    created_at: str
    updated_at: str


class FixedAssetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_count: int = Field(ge=0)
    active_count: int = Field(ge=0)
    disposed_count: int = Field(ge=0)
    sold_count: int = Field(ge=0)
    original_cost_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    accumulated_depreciation_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    net_book_value_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    monthly_depreciation_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class FixedAssetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    summary: FixedAssetSummary
    assets: list[FixedAssetRecord]


class FixedAssetDepreciationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=PERIOD_PATTERN)
    operator: str = Field(default="财务主管", min_length=1, max_length=60)


class FixedAssetDepreciationRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    operator: str
    depreciated_count: int = Field(ge=0)
    total_depreciation: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    assets: list[FixedAssetRecord]


class FixedAssetDisposeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposal_date: str = Field(pattern=DATE_PATTERN)
    reason: str = Field(min_length=1, max_length=200)
    operator: str = Field(default="财务主管", min_length=1, max_length=60)


class FixedAssetSaleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sale_date: str = Field(pattern=DATE_PATTERN)
    sale_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    reason: str = Field(min_length=1, max_length=200)
    operator: str = Field(default="财务主管", min_length=1, max_length=60)


class FixedAssetInventoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inventory_date: str = Field(pattern=DATE_PATTERN)
    location: str = Field(min_length=1, max_length=120)
    custodian: str = Field(min_length=1, max_length=80)
    condition: str = Field(min_length=1, max_length=80)
    operator: str = Field(default="盘点员", min_length=1, max_length=60)
    note: str | None = Field(default=None, max_length=200)
