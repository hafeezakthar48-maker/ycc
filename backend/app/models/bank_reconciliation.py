from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.receivable_payable import CounterpartySettlementCreate


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


class BankStatementImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    lines: list[BankStatementLineCreate] = Field(min_length=1, max_length=500)


class BankMatchCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement_line_id: str
    journal_entry_id: str
    journal_line_id: str
    direction: BankTransactionDirection
    score: int = Field(ge=0, le=100)
    reasons: list[str]
    statement_date: str
    journal_date: str
    statement_amount: Decimal
    journal_amount: Decimal
    currency: str
    counterparty_name: str = ""
    summary: str = ""


class BankMatchCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    bank_account_id: str
    period: str
    minimum_score: int
    candidates: list[BankMatchCandidate]


class BankReconciliationConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    bank_account_id: str = Field(min_length=1, max_length=80)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    statement_line_ids: list[str] = Field(min_length=1, max_length=100)
    journal_line_ids: list[str] = Field(min_length=1, max_length=100)
    confirmed_by: str = Field(min_length=1, max_length=60)
    note: str = Field(default="", max_length=200)
    receivable_payable_settlement: CounterpartySettlementCreate | None = None


class BankReconciliationMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reconciliation_id: str
    account_set_id: str
    bank_account_id: str
    period: str
    statement_line_ids: list[str]
    journal_line_ids: list[str]
    status: Literal["matched", "reversed"] = "matched"
    confirmed_by: str
    confirmed_at: str
    note: str = ""
    settlement_ids: list[str] = Field(default_factory=list)


class BankBalanceReconciliationStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    bank_account_id: str
    period: str
    bank_balance: Decimal
    book_balance: Decimal
    bank_received_not_booked: Decimal
    bank_paid_not_booked: Decimal
    book_received_not_bank: Decimal
    book_paid_not_bank: Decimal
    adjusted_bank_balance: Decimal
    adjusted_book_balance: Decimal
    unmatched_statement_count: int
    unmatched_journal_count: int
    unmatched_statement_lines: list[BankStatementLine]
    unmatched_journal_lines: list[dict]
