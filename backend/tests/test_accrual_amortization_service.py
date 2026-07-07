from decimal import Decimal

from app.models.accrual_amortization import AccountingScheduleCreate
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import list_journal_entries, reset_accounting_store
from app.services.accrual_amortization_service import (
    calculate_even_monthly_amount,
    create_accounting_schedule,
    post_schedule_for_period,
    reset_accrual_amortization_store,
)


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()
    reset_accrual_amortization_store()


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


def test_calculate_even_monthly_amount_rounds_to_cents():
    result = calculate_even_monthly_amount(Decimal("10000.00"), 3)

    assert result == [Decimal("3333.33"), Decimal("3333.33"), Decimal("3333.34")]


def test_post_prepaid_amortization_for_period_uses_schedule_source_key():
    create_accounting_schedule(
        AccountingScheduleCreate(
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
    )

    entry = post_schedule_for_period("default", "AMORT-2026-001", "2026-06", "close-user")
    duplicate = post_schedule_for_period("default", "AMORT-2026-001", "2026-06", "close-user")
    entries = list_journal_entries("default", "2026-06").entries

    assert entry.source_id == "schedule_posting:default:2026-06:AMORT-2026-001"
    assert duplicate.id == entry.id
    assert [(line.account_code, line.direction, line.base_amount) for line in entry.lines] == [
        ("6602", "debit", Decimal("1000.00")),
        ("1801", "credit", Decimal("1000.00")),
    ]
    assert [entry.source_type for entry in entries].count("prepaid_amortization") == 1
