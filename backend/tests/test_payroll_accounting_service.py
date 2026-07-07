from decimal import Decimal

from app.models.payroll_accounting import PayrollAccountingBatchCreate


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
