from decimal import Decimal

import pytest
from fastapi import HTTPException

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


def test_pay_payroll_batch_posts_deductions_and_bank_payment():
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
    from app.services.payroll_accounting_service import accrue_payroll_batch, pay_payroll_batch

    accrue_payroll_batch("default", "2026-06", "PAY-2026-06", "payroll-user")

    result = pay_payroll_batch("default", "2026-06", "PAY-2026-06", "1002", "payroll-user")

    assert result.source_type == "payroll_payment"
    assert result.source_id == "payroll_payment:default:2026-06:PAY-2026-06"
    assert [(line.account_code, line.direction, line.base_amount) for line in result.lines] == [
        ("2211", "debit", Decimal("10000.00")),
        ("2241", "credit", Decimal("1750.00")),
        ("2221", "credit", Decimal("115.00")),
        ("1002", "credit", Decimal("8135.00")),
    ]


def test_pay_payroll_batch_requires_accrual_entry():
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
    from app.services.payroll_accounting_service import pay_payroll_batch

    with pytest.raises(HTTPException) as exc_info:
        pay_payroll_batch("default", "2026-06", "PAY-2026-06", "1002", "payroll-user")

    assert exc_info.value.status_code == 409


def test_remit_payroll_liabilities_posts_tax_and_social_security_payments():
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
    from app.services.payroll_accounting_service import accrue_payroll_batch, pay_payroll_batch, remit_payroll_liabilities

    accrue_payroll_batch("default", "2026-06", "PAY-2026-06", "payroll-user")
    pay_payroll_batch("default", "2026-06", "PAY-2026-06", "1002", "payroll-user")

    result = remit_payroll_liabilities("default", "2026-07", "PAY-2026-06", "1002", "payroll-user")

    assert result.source_type == "payroll_liability_payment"
    assert result.source_id == "payroll_liability_payment:default:2026-07:PAY-2026-06"
    assert [(line.account_code, line.direction, line.base_amount) for line in result.lines] == [
        ("2211", "debit", Decimal("3330.00")),
        ("2241", "debit", Decimal("1750.00")),
        ("2221", "debit", Decimal("115.00")),
        ("1002", "credit", Decimal("5195.00")),
    ]
