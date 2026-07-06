from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CounterpartyType = Literal["customer", "supplier"]
OpenItemType = Literal["receivable", "payable"]
SettlementStatus = Literal["open", "partial", "settled", "written_off"]
AgingBucketCode = Literal["0-30", "31-60", "61-90", "91-180", "181-365", "365+"]


class CounterpartyOpenItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open_item_id: str
    account_set_id: str
    open_item_type: OpenItemType
    period: str
    source_entry_id: str
    source_line_id: str
    source_type: str
    source_id: str
    document_date: str
    due_date: str | None = None
    account_code: str
    account_name: str
    counterparty_type: CounterpartyType
    counterparty_code: str
    counterparty_name: str
    currency: str = "CNY"
    original_amount: Decimal
    base_amount: Decimal
    settled_base_amount: Decimal = Decimal("0.00")
    open_base_amount: Decimal
    status: SettlementStatus = "open"


class CounterpartyBalanceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counterparty_type: CounterpartyType
    counterparty_code: str
    counterparty_name: str
    open_item_type: OpenItemType
    currency: str = "CNY"
    original_balance: Decimal
    base_balance: Decimal
    open_item_count: int


class CounterpartyBalanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    open_item_type: OpenItemType
    total_base_balance: Decimal
    item_count: int
    items: list[CounterpartyBalanceItem]


class AgingBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bucket_code: AgingBucketCode
    day_from: int
    day_to: int | None
    amount: Decimal
    open_item_count: int


class CounterpartyAgingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counterparty_type: CounterpartyType
    counterparty_code: str
    counterparty_name: str
    buckets: list[AgingBucket]
    total_base_balance: Decimal


class CounterpartyAgingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    as_of_date: str
    open_item_type: OpenItemType
    buckets: list[AgingBucket]
    items: list[CounterpartyAgingItem]
    total_base_balance: Decimal
