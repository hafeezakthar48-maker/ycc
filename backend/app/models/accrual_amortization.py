from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ScheduleType = Literal["prepaid_amortization", "accrued_expense", "deferred_revenue", "loan_interest"]
ScheduleStatus = Literal["active", "paused", "completed", "terminated"]


class AccountingScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    schedule_code: str = Field(min_length=1, max_length=80)
    schedule_type: ScheduleType
    start_period: str = Field(pattern=r"^\d{4}-\d{2}$")
    end_period: str = Field(pattern=r"^\d{4}-\d{2}$")
    total_amount: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=2)
    debit_account_code: str = Field(min_length=1, max_length=32)
    credit_account_code: str = Field(min_length=1, max_length=32)
    department_id: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=64)


class AccountingSchedule(AccountingScheduleCreate):
    status: ScheduleStatus = "active"
    posted_periods: list[str] = Field(default_factory=list)


class LoanScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    loan_code: str = Field(min_length=1, max_length=80)
    principal: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=2)
    annual_rate: Decimal = Field(gt=Decimal("0"), max_digits=10, decimal_places=6)
    start_period: str = Field(pattern=r"^\d{4}-\d{2}$")
    end_period: str = Field(pattern=r"^\d{4}-\d{2}$")
    loan_account_code: str = Field(default="2001", min_length=1, max_length=32)
    interest_expense_account_code: str = Field(default="6603", min_length=1, max_length=32)
    interest_payable_account_code: str = Field(default="2231", min_length=1, max_length=32)


class LoanSchedule(LoanScheduleCreate):
    status: ScheduleStatus = "active"
    interest_posted_periods: list[str] = Field(default_factory=list)


class AccountingScheduleListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    total_schedules: int
    total_loans: int
    schedules: list[AccountingSchedule]
    loan_schedules: list[LoanSchedule]


class SchedulePostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")


class LoanInterestPostRequest(LoanScheduleCreate):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
