from decimal import Decimal
from typing import Literal

from app.models.accounting import JournalEntryRecord
from pydantic import BaseModel, ConfigDict, Field


FormalAssetAccountingStatus = Literal[
    "not_capitalized",
    "capitalized",
    "depreciating",
    "impaired",
    "disposed",
    "sold",
]
FormalAssetLifecycleStatus = Literal["active", "disposed", "sold"]
FixedAssetAccountingBatchStatus = Literal["generated", "existing", "skipped"]


class FormalAssetAccountingCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(min_length=1, max_length=64)
    asset_id: str = Field(min_length=1, max_length=80)
    asset_code: str = Field(min_length=1, max_length=80)
    asset_name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    acquisition_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    original_cost: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    salvage_value: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    useful_life_months: int = Field(ge=1, le=600)
    monthly_depreciation: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    accumulated_depreciation: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    impairment_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    net_book_value: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    asset_status: FormalAssetLifecycleStatus
    formal_accounting_status: FormalAssetAccountingStatus
    capitalization_entry_id: str | None = None
    last_depreciation_entry_id: str | None = None
    last_depreciated_period: str | None = None
    impairment_entry_ids: list[str] = Field(default_factory=list)
    disposal_entry_ids: list[str] = Field(default_factory=list)


class FixedAssetAccountingEntryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    status: FixedAssetAccountingBatchStatus
    depreciated_count: int = Field(ge=0)
    total_depreciation: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    entries: list[JournalEntryRecord]
