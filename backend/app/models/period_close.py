from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PeriodCloseStatus = Literal["draft", "checking", "ready", "generated", "closed", "reopened", "failed"]
PeriodCloseType = Literal["month", "year"]
PeriodCloseActionType = Literal[
    "fixed_asset_depreciation",
    "payroll_accrual",
    "tax_accrual",
    "fx_revaluation",
    "profit_loss_carryforward",
    "year_end_profit_distribution",
]


class PeriodCloseRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    close_type: PeriodCloseType = "month"
    requested_by: str = Field(min_length=1, max_length=60)


class PeriodCloseRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    account_set_id: str
    period: str
    close_type: PeriodCloseType
    status: PeriodCloseStatus
    requested_by: str
    created_at: str
    updated_at: str
    closed_at: str | None = None
    reopened_at: str | None = None


class PeriodCloseRunListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str | None = None
    total: int
    runs: list[PeriodCloseRun]


class PeriodCloseCheckItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_code: str
    check_name: str
    status: Literal["passed", "failed", "warning"]
    severity: Literal["blocker", "warning"]
    message: str
    evidence: dict[str, str | int | Decimal] = Field(default_factory=dict)


class PeriodCloseActionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: PeriodCloseActionType
    status: Literal["skipped", "generated", "existing", "failed"]
    journal_entry_ids: list[str] = Field(default_factory=list)
    amount: Decimal = Decimal("0.00")
    message: str


class TaxAccrualRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    tax_code: str = Field(min_length=1, max_length=40)
    tax_name: str = Field(min_length=1, max_length=80)
    rate: Decimal = Field(gt=0, max_digits=10, decimal_places=6)
    base_account_codes: list[str] = Field(min_length=1, max_length=20)
    debit_account_code: str = Field(min_length=1, max_length=32)
    credit_account_code: str = Field(default="2221", min_length=1, max_length=32)
