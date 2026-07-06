from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LedgerAccountSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_code: str
    account_name: str
    debit_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    credit_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    balance_direction: Literal["借", "贷", "平"]
    balance_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    entry_count: int = Field(ge=0)


class LedgerDetailLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voucher_id: str
    voucher_number: str
    voucher_date: str
    summary: str
    counterparty: str
    account_code: str
    account_name: str
    direction: Literal["借", "贷"]
    explanation: str
    debit_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    credit_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    status: str


class GeneralLedgerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str
    voucher_count: int = Field(ge=0)
    entry_count: int = Field(ge=0)
    total_debit: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    total_credit: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    balanced: bool
    accounts: list[LedgerAccountSummary]


class DetailLedgerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str
    account_code: str
    account_name: str
    line_count: int = Field(ge=0)
    debit_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    credit_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    balance_direction: Literal["借", "贷", "平"]
    balance_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    lines: list[LedgerDetailLine]


class AccountBalanceTableResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str
    account_count: int = Field(ge=0)
    total_debit: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    total_credit: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    balanced: bool
    accounts: list[LedgerAccountSummary]
