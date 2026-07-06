from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AccountType = Literal["asset", "liability", "equity", "revenue", "cost", "expense"]
NormalBalance = Literal["debit", "credit"]
JournalDirection = Literal["debit", "credit"]
JournalStatus = Literal["posted", "reversed"]
LedgerSource = Literal["formal_journal_entries", "mvp_voucher_workflow", "sample_finance_data"]


class AccountItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    account_code: str
    account_name: str
    account_type: AccountType
    normal_balance: NormalBalance
    is_active: bool = True


class AccountListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    accounts: list[AccountItem]


class JournalLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_code: str = Field(min_length=1, max_length=32)
    account_name: str = Field(min_length=1, max_length=80)
    direction: JournalDirection
    currency: str = Field(default="CNY", min_length=3, max_length=3)
    original_amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    exchange_rate: Decimal = Field(default=Decimal("1.000000"), gt=0, max_digits=18, decimal_places=6)
    base_amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    description: str = Field(default="", max_length=200)


class JournalEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    entry_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    source_type: str = Field(min_length=1, max_length=40)
    source_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    base_currency: str = Field(default="CNY", min_length=3, max_length=3)
    created_by: str = Field(default="system", min_length=1, max_length=60)
    posted_by: str = Field(default="system", min_length=1, max_length=60)
    lines: list[JournalLineCreate] = Field(min_length=2, max_length=100)


class JournalLineRecord(JournalLineCreate):
    id: str
    journal_entry_id: str
    line_no: int


class JournalEntryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    account_set_id: str
    period: str
    entry_date: str
    entry_number: str
    source_type: str
    source_id: str
    description: str
    status: JournalStatus
    base_currency: str
    created_by: str
    posted_by: str
    posted_at: str
    reversal_of_entry_id: str | None = None
    lines: list[JournalLineRecord]


class JournalEntryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str | None = None
    total: int
    entries: list[JournalEntryRecord]
