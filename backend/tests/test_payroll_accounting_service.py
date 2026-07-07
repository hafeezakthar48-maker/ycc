from decimal import Decimal

from app.models.payroll import PayrollCalculateRequest, PayrollEmployeeInput
from app.models.payroll_accounting import PayrollAccountingBatchCreate
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import reset_accounting_store
from app.services.payroll_service import calculate_payroll, reset_payroll_store


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()
    reset_payroll_store()


def test_payroll_accounting_batch_keeps_amount_breakdown():
    batch = PayrollAccountingBatchCreate(
        account_set_id="default",
        period="2026-06",
        payroll_batch_id="PAY-2026-06",
        gross_salary=Decimal("100000.00"),
        employee_social_security=Decimal("10500.00"),
        employee_housing_fund=Decimal("7000.00"),
        individual_income_tax=Decimal("3000.00"),
        net_salary=Decimal("79500.00"),
        employer_social_security=Decimal("26300.00"),
        employer_housing_fund=Decimal("7000.00"),
    )

    assert batch.net_salary == Decimal("79500.00")


def test_accrue_payroll_batch_creates_salary_and_employer_cost_entry():
    calculate_payroll(
        PayrollCalculateRequest(
            account_set_id="default",
            period="2026-06",
            employees=[
                PayrollEmployeeInput(
                    employee_id="E001",
                    employee_name="张会计",
                    department="财务部",
                    base_salary=Decimal("10000.00"),
                    social_security_base=Decimal("10000.00"),
                    housing_fund_base=Decimal("10000.00"),
                )
            ],
        )
    )

    from app.services.payroll_accounting_service import accrue_payroll_batch

    result = accrue_payroll_batch("default", "2026-06", "PAY-2026-06", "payroll-user")

    assert result.source_type == "payroll_accrual"
    assert result.source_id == "payroll_accrual:default:2026-06:PAY-2026-06"
    assert result.id.startswith("je-")
    assert [(line.account_code, line.direction, line.base_amount) for line in result.lines] == [
        ("6602", "debit", Decimal("10000.00")),
        ("6602", "debit", Decimal("3330.00")),
        ("2211", "credit", Decimal("10000.00")),
        ("2211", "credit", Decimal("3330.00")),
    ]
