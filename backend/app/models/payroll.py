from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


PERIOD_PATTERN = r"^\d{4}-\d{2}$"


class PayrollEmployeeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str = Field(min_length=1, max_length=40)
    employee_name: str = Field(min_length=1, max_length=80)
    department: str = Field(min_length=1, max_length=80)
    base_salary: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    bonus: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    allowance: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    social_security_base: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    housing_fund_base: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    special_additional_deduction: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    other_deduction: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)


class PayrollCalculateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=PERIOD_PATTERN)
    operator: str = Field(default="财务主管", min_length=1, max_length=60)
    employees: list[PayrollEmployeeInput] = Field(min_length=1, max_length=500)


class PayrollEmployeeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str
    employee_name: str
    department: str
    gross_pay: Decimal
    employee_social_security: Decimal
    employer_social_security: Decimal
    employee_housing_fund: Decimal
    employer_housing_fund: Decimal
    special_additional_deduction: Decimal
    taxable_income: Decimal
    tax_rate: Decimal
    quick_deduction: Decimal
    individual_income_tax: Decimal
    other_deduction: Decimal
    net_pay: Decimal
    employer_cost: Decimal


class PayrollSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_count: int = Field(ge=0)
    gross_pay_total: Decimal
    employee_social_security_total: Decimal
    employer_social_security_total: Decimal
    employee_housing_fund_total: Decimal
    employer_housing_fund_total: Decimal
    individual_income_tax_total: Decimal
    net_pay_total: Decimal
    employer_cost_total: Decimal
    average_net_pay: Decimal


class PayrollDepartmentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department: str
    employee_count: int = Field(ge=0)
    gross_pay_total: Decimal
    net_pay_total: Decimal
    employer_cost_total: Decimal


class PayrollCalculationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    operator: str
    summary: PayrollSummary
    employees: list[PayrollEmployeeResult]
    department_analysis: list[PayrollDepartmentSummary]
