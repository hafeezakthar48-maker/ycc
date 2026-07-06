from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


BankTransactionDirection = Literal["inflow", "outflow"]
BankMatchStatus = Literal["unmatched", "suggested", "matched", "ignored"]


class BankAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    bank_account_id: str = Field(min_length=1, max_length=80)
    bank_name: str = Field(min_length=1, max_length=120)
    account_number_masked: str = Field(min_length=1, max_length=80)
    currency: str = Field(default="CNY", min_length=3, max_length=3)
    linked_account_code: str = Field(default="1002", min_length=1, max_length=32)
    enabled: bool = True


class BankStatementLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    bank_account_id: str = Field(min_length=1, max_length=80)
    transaction_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    direction: BankTransactionDirection
    amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    currency: str = Field(default="CNY", min_length=3, max_length=3)
    counterparty_name: str = Field(default="", max_length=120)
    summary: str = Field(default="", max_length=200)
    bank_reference: str = Field(min_length=1, max_length=120)


class BankStatementLine(BankStatementLineCreate):
    statement_line_id: str
    imported_at: str
    match_status: BankMatchStatus = "unmatched"


class BankStatementImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    imported_count: int
    duplicate_count: int
    lines: list[BankStatementLine]
