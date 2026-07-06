from decimal import Decimal
from typing import Literal

from app.models.finance_qa import FinanceCitation
from pydantic import BaseModel, ConfigDict, Field


DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class AuditVoucherLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_code: str = Field(min_length=1, max_length=32)
    account_name: str = Field(min_length=1, max_length=80)
    direction: Literal["借", "贷"]
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    explanation: str = Field(default="", max_length=200)


class AuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_subject: Literal["voucher"] = "voucher"
    voucher_date: str = Field(pattern=DATE_PATTERN)
    summary: str = Field(default="", max_length=200)
    counterparty: str = Field(default="", max_length=120)
    invoice_number: str | None = Field(default=None, max_length=40)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    tax_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    total_amount_with_tax: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    lines: list[AuditVoucherLine] = Field(min_length=1, max_length=50)


class AuditCheck(BaseModel):
    id: str
    title: str
    status: str
    evidence: str


class AuditFinding(BaseModel):
    id: str
    title: str
    category: str
    severity: int = Field(ge=1, le=5)
    description: str
    evidence: str
    suggestion: str


class AuditResponse(BaseModel):
    rating: str
    score: int = Field(ge=0, le=100)
    checks: list[AuditCheck]
    findings: list[AuditFinding]
    suggestions: list[str]
    citations: list[FinanceCitation]
    requires_human_review: bool = True
