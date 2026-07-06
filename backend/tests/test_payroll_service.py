from decimal import Decimal

import pytest

from app.models.payroll import PayrollCalculateRequest, PayrollEmployeeInput
from app.services.payroll_service import calculate_payroll


def _employee(
    employee_id: str,
    employee_name: str,
    department: str,
    base_salary: str,
    *,
    bonus: str = "0.00",
    allowance: str = "0.00",
    special_additional_deduction: str = "0.00",
) -> PayrollEmployeeInput:
    gross_base = Decimal(base_salary)
    return PayrollEmployeeInput(
        employee_id=employee_id,
        employee_name=employee_name,
        department=department,
        base_salary=gross_base,
        bonus=Decimal(bonus),
        allowance=Decimal(allowance),
        social_security_base=gross_base,
        housing_fund_base=gross_base,
        special_additional_deduction=Decimal(special_additional_deduction),
    )


def test_payroll_calculates_social_security_housing_tax_and_net_pay():
    request = PayrollCalculateRequest(
        account_set_id="default",
        period="2026-06",
        employees=[
            _employee(
                "E001",
                "张会计",
                "财务部",
                "20000.00",
                special_additional_deduction="1000.00",
            )
        ],
    )

    result = calculate_payroll(request)
    employee = result.employees[0]

    assert result.period == "2026-06"
    assert employee.gross_pay == Decimal("20000.00")
    assert employee.employee_social_security == Decimal("2100.00")
    assert employee.employee_housing_fund == Decimal("1400.00")
    assert employee.taxable_income == Decimal("10500.00")
    assert employee.individual_income_tax == Decimal("840.00")
    assert employee.net_pay == Decimal("15660.00")
    assert employee.employer_social_security == Decimal("5260.00")
    assert employee.employer_housing_fund == Decimal("1400.00")
    assert employee.employer_cost == Decimal("26660.00")
    assert employee.tax_rate == Decimal("0.10")
    assert employee.quick_deduction == Decimal("210.00")


def test_payroll_summarizes_totals_and_department_analysis():
    request = PayrollCalculateRequest(
        account_set_id="default",
        period="2026-06",
        employees=[
            _employee("E001", "张会计", "财务部", "20000.00", special_additional_deduction="1000.00"),
            _employee("E002", "李运营", "运营部", "8000.00"),
        ],
    )

    result = calculate_payroll(request)
    finance = next(item for item in result.department_analysis if item.department == "财务部")
    operation = next(item for item in result.department_analysis if item.department == "运营部")

    assert result.summary.employee_count == 2
    assert result.summary.gross_pay_total == Decimal("28000.00")
    assert result.summary.employee_social_security_total == Decimal("2940.00")
    assert result.summary.employee_housing_fund_total == Decimal("1960.00")
    assert result.summary.individual_income_tax_total == Decimal("888.00")
    assert result.summary.net_pay_total == Decimal("22212.00")
    assert result.summary.employer_cost_total == Decimal("37324.00")
    assert result.summary.average_net_pay == Decimal("11106.00")
    assert finance.employee_count == 1
    assert finance.net_pay_total == Decimal("15660.00")
    assert operation.employee_count == 1
    assert operation.net_pay_total == Decimal("6552.00")


def test_payroll_calculation_is_isolated_by_account_set_metadata():
    request = PayrollCalculateRequest(
        account_set_id="cross_border",
        period="2026-06",
        employees=[_employee("E003", "王跨境", "跨境运营部", "12000.00")],
    )

    result = calculate_payroll(request)

    assert result.account_set_id == "cross_border"
    assert result.employees[0].employee_name == "王跨境"
    assert result.summary.net_pay_total == Decimal("9620.00")
