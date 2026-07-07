from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PayrollAccountingStatus = Literal["calculated", "accrued", "paid", "reversed"]


class PayrollAccountingBatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    payroll_batch_id: str = Field(min_length=1, max_length=80)
    gross_salary: Decimal = Field(ge=Decimal("0.00"), max_digits=16, decimal_places=2)
    employee_social_security: Decimal = Field(ge=Decimal("0.00"), max_digits=16, decimal_places=2)
    employee_housing_fund: Decimal = Field(ge=Decimal("0.00"), max_digits=16, decimal_places=2)
    individual_income_tax: Decimal = Field(ge=Decimal("0.00"), max_digits=16, decimal_places=2)
    net_salary: Decimal = Field(ge=Decimal("0.00"), max_digits=16, decimal_places=2)
    employer_social_security: Decimal = Field(ge=Decimal("0.00"), max_digits=16, decimal_places=2)
    employer_housing_fund: Decimal = Field(ge=Decimal("0.00"), max_digits=16, decimal_places=2)


class PayrollAccountingBatch(PayrollAccountingBatchCreate):
    status: PayrollAccountingStatus = "calculated"
    accrual_journal_entry_id: str | None = None
    payment_journal_entry_id: str | None = None
