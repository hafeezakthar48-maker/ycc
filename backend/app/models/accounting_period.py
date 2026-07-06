from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AccountSetItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    base_currency: str = Field(min_length=3, max_length=3)
    accounting_standard: str = Field(min_length=1)
    is_default: bool


class AccountSetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_sets: list[AccountSetItem]


class AccountingPeriodItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(min_length=1)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    status: Literal["open", "closed"]
    closed_by: str | None = None
    closed_at: str | None = None
    voucher_count: int = Field(ge=0)
    posted_voucher_count: int = Field(ge=0)


class AccountingPeriodListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    periods: list[AccountingPeriodItem]


class PeriodStatusChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: str = Field(default="财务主管", min_length=1, max_length=60)
