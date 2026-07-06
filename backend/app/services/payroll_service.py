from decimal import Decimal, ROUND_HALF_UP

from app.models.payroll import (
    PayrollCalculateRequest,
    PayrollCalculationResponse,
    PayrollDepartmentSummary,
    PayrollEmployeeInput,
    PayrollEmployeeResult,
    PayrollSummary,
)
from app.services.accounting_period_service import validate_account_set


MONEY_ZERO = Decimal("0.00")
MONEY_QUANT = Decimal("0.01")
BASIC_DEDUCTION = Decimal("5000.00")
EMPLOYEE_SOCIAL_SECURITY_RATE = Decimal("0.105")
EMPLOYER_SOCIAL_SECURITY_RATE = Decimal("0.263")
HOUSING_FUND_RATE = Decimal("0.07")
MONTHLY_TAX_BRACKETS: tuple[tuple[Decimal, Decimal, Decimal], ...] = (
    (Decimal("3000.00"), Decimal("0.03"), Decimal("0.00")),
    (Decimal("12000.00"), Decimal("0.10"), Decimal("210.00")),
    (Decimal("25000.00"), Decimal("0.20"), Decimal("1410.00")),
    (Decimal("35000.00"), Decimal("0.25"), Decimal("2660.00")),
    (Decimal("55000.00"), Decimal("0.30"), Decimal("4410.00")),
    (Decimal("80000.00"), Decimal("0.35"), Decimal("7160.00")),
    (Decimal("999999999.00"), Decimal("0.45"), Decimal("15160.00")),
)

_payroll_calculations: dict[tuple[str, str], PayrollCalculationResponse] = {}


def reset_payroll_store() -> None:
    _payroll_calculations.clear()


def calculate_payroll(request: PayrollCalculateRequest) -> PayrollCalculationResponse:
    validate_account_set(request.account_set_id)
    employees = [_calculate_employee(employee) for employee in request.employees]
    response = PayrollCalculationResponse(
        account_set_id=request.account_set_id,
        period=request.period,
        operator=request.operator,
        summary=_summary(employees),
        employees=employees,
        department_analysis=_department_analysis(employees),
    )
    _payroll_calculations[(request.account_set_id, request.period)] = response
    return response


def get_period_payroll_accrual_summary(account_set_id: str, period: str) -> list[dict]:
    validate_account_set(account_set_id)
    response = _payroll_calculations.get((account_set_id, period))
    if response is None:
        return []
    rows = [
        {
            "department": item.department,
            "amount": _money(item.employer_cost_total),
            "debit_account_code": "6602",
            "credit_account_code": "2211",
        }
        for item in response.department_analysis
        if item.employer_cost_total > MONEY_ZERO
    ]
    rows.sort(key=lambda row: row["department"])
    return rows


def _calculate_employee(employee: PayrollEmployeeInput) -> PayrollEmployeeResult:
    gross_pay = _money(employee.base_salary + employee.bonus + employee.allowance)
    employee_social_security = _money(employee.social_security_base * EMPLOYEE_SOCIAL_SECURITY_RATE)
    employer_social_security = _money(employee.social_security_base * EMPLOYER_SOCIAL_SECURITY_RATE)
    employee_housing_fund = _money(employee.housing_fund_base * HOUSING_FUND_RATE)
    employer_housing_fund = _money(employee.housing_fund_base * HOUSING_FUND_RATE)
    taxable_income = max(
        MONEY_ZERO,
        _money(
            gross_pay
            - employee_social_security
            - employee_housing_fund
            - BASIC_DEDUCTION
            - employee.special_additional_deduction
        ),
    )
    tax_rate, quick_deduction = _tax_bracket(taxable_income)
    individual_income_tax = _money(max(MONEY_ZERO, taxable_income * tax_rate - quick_deduction))
    other_deduction = _money(employee.other_deduction)
    net_pay = _money(gross_pay - employee_social_security - employee_housing_fund - individual_income_tax - other_deduction)
    employer_cost = _money(gross_pay + employer_social_security + employer_housing_fund)
    return PayrollEmployeeResult(
        employee_id=employee.employee_id,
        employee_name=employee.employee_name,
        department=employee.department,
        gross_pay=gross_pay,
        employee_social_security=employee_social_security,
        employer_social_security=employer_social_security,
        employee_housing_fund=employee_housing_fund,
        employer_housing_fund=employer_housing_fund,
        special_additional_deduction=_money(employee.special_additional_deduction),
        taxable_income=taxable_income,
        tax_rate=tax_rate,
        quick_deduction=quick_deduction,
        individual_income_tax=individual_income_tax,
        other_deduction=other_deduction,
        net_pay=net_pay,
        employer_cost=employer_cost,
    )


def _summary(employees: list[PayrollEmployeeResult]) -> PayrollSummary:
    employee_count = len(employees)
    net_pay_total = _sum_money(employee.net_pay for employee in employees)
    return PayrollSummary(
        employee_count=employee_count,
        gross_pay_total=_sum_money(employee.gross_pay for employee in employees),
        employee_social_security_total=_sum_money(employee.employee_social_security for employee in employees),
        employer_social_security_total=_sum_money(employee.employer_social_security for employee in employees),
        employee_housing_fund_total=_sum_money(employee.employee_housing_fund for employee in employees),
        employer_housing_fund_total=_sum_money(employee.employer_housing_fund for employee in employees),
        individual_income_tax_total=_sum_money(employee.individual_income_tax for employee in employees),
        net_pay_total=net_pay_total,
        employer_cost_total=_sum_money(employee.employer_cost for employee in employees),
        average_net_pay=_money(net_pay_total / Decimal(employee_count)) if employee_count else MONEY_ZERO,
    )


def _department_analysis(employees: list[PayrollEmployeeResult]) -> list[PayrollDepartmentSummary]:
    departments: dict[str, list[PayrollEmployeeResult]] = {}
    for employee in employees:
        departments.setdefault(employee.department, []).append(employee)

    results = []
    for department, department_employees in sorted(departments.items()):
        results.append(
            PayrollDepartmentSummary(
                department=department,
                employee_count=len(department_employees),
                gross_pay_total=_sum_money(employee.gross_pay for employee in department_employees),
                net_pay_total=_sum_money(employee.net_pay for employee in department_employees),
                employer_cost_total=_sum_money(employee.employer_cost for employee in department_employees),
            )
        )
    return results


def _tax_bracket(taxable_income: Decimal) -> tuple[Decimal, Decimal]:
    if taxable_income <= MONEY_ZERO:
        return MONEY_ZERO, MONEY_ZERO
    for limit, tax_rate, quick_deduction in MONTHLY_TAX_BRACKETS:
        if taxable_income <= limit:
            return tax_rate, quick_deduction
    return MONTHLY_TAX_BRACKETS[-1][1], MONTHLY_TAX_BRACKETS[-1][2]


def _sum_money(values) -> Decimal:
    return _money(sum(values, MONEY_ZERO))


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
