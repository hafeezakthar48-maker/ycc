from decimal import Decimal
from typing import Literal

from app.models.finance_qa import FinanceCitation
from pydantic import BaseModel, ConfigDict, Field


DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class VoucherDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_type: str = Field(min_length=1, max_length=60)
    voucher_date: str = Field(pattern=DATE_PATTERN)
    counterparty: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    tax_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    total_amount_with_tax: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    payment_status: str = "unpaid"
    memo: str = Field(default="", max_length=200)


class VoucherLine(BaseModel):
    account_code: str
    account_name: str
    direction: Literal["借", "贷"]
    amount: Decimal
    explanation: str


class VoucherRiskItem(BaseModel):
    id: str
    title: str
    level: int = Field(ge=1, le=5)
    description: str
    suggestion: str


class VoucherDraftResponse(BaseModel):
    scenario_label: str
    voucher_date: str
    summary: str
    lines: list[VoucherLine]
    debit_total: Decimal
    credit_total: Decimal
    balanced: bool
    risks: list[VoucherRiskItem]
    suggestions: list[str]
    citations: list[FinanceCitation]
    requires_human_review: bool = True
