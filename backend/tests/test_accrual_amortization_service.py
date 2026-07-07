from decimal import Decimal

from app.models.accrual_amortization import AccountingScheduleCreate


def test_accounting_schedule_has_total_amount_and_months():
    schedule = AccountingScheduleCreate(
        account_set_id="default",
        schedule_code="AMORT-2026-001",
        schedule_type="prepaid_amortization",
        start_period="2026-01",
        end_period="2026-12",
        total_amount=Decimal("12000.00"),
        debit_account_code="6602",
        credit_account_code="1801",
        department_id="dept-admin",
    )

    assert schedule.total_amount == Decimal("12000.00")
