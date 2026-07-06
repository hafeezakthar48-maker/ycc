from decimal import Decimal

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.models.fixed_asset import FixedAssetCreateRequest
from app.models.payroll import PayrollCalculateRequest, PayrollEmployeeInput
from app.models.period_close import PeriodCloseRunCreate, TaxAccrualRule
from app.services.accounting_service import list_journal_entries, post_journal_entry, reset_accounting_store
from app.services.fixed_asset_service import create_fixed_asset, reset_fixed_asset_store
from app.services.payroll_service import calculate_payroll, reset_payroll_store
from app.services.period_close_service import (
    generate_period_close_actions,
    get_period_close_run,
    list_period_close_runs,
    reset_period_close_store,
    run_period_close_checks,
    set_tax_accrual_rules,
    start_period_close_run,
)


def setup_function():
    reset_accounting_store()
    reset_fixed_asset_store()
    reset_payroll_store()
    reset_period_close_store()


def test_start_period_close_run_records_scope_and_status():
    run = start_period_close_run(
        PeriodCloseRunCreate(
            account_set_id="default",
            period="2026-06",
            close_type="month",
            requested_by="finance-user",
        )
    )

    loaded = get_period_close_run(run.run_id)
    listed = list_period_close_runs("default", period="2026-06")

    assert run.status == "draft"
    assert loaded.account_set_id == "default"
    assert listed.total == 1


def test_period_close_checks_return_required_items():
    items = run_period_close_checks(account_set_id="default", period="2026-06")

    assert any(item.check_code == "journal_entries_balanced" for item in items)
    assert all(item.severity in {"blocker", "warning"} for item in items)


def test_generate_fixed_asset_depreciation_action_posts_entry_and_is_idempotent():
    create_fixed_asset(
        FixedAssetCreateRequest(
            name="生产设备",
            category="设备",
            acquisition_date="2026-01-15",
            original_cost=Decimal("120000.00"),
            salvage_value=Decimal("12000.00"),
            useful_life_months=60,
        )
    )

    first = generate_period_close_actions(
        account_set_id="default",
        period="2026-06",
        actions=["fixed_asset_depreciation"],
        generated_by="finance-user",
    )
    second = generate_period_close_actions(
        account_set_id="default",
        period="2026-06",
        actions=["fixed_asset_depreciation"],
        generated_by="finance-user",
    )
    entries = list_journal_entries("default", "2026-06").entries

    assert first[0].status == "generated"
    assert first[0].amount == Decimal("1800.00")
    assert second[0].status == "existing"
    assert [entry.source_type for entry in entries].count("fixed_asset_depreciation") == 1


def test_generate_payroll_accrual_action_uses_calculated_payroll_summary():
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

    results = generate_period_close_actions(
        account_set_id="default",
        period="2026-06",
        actions=["payroll_accrual"],
        generated_by="finance-user",
    )

    assert results[0].status == "generated"
    assert results[0].amount == Decimal("13330.00")


def test_generate_tax_accrual_action_uses_configured_rule():
    post_journal_entry(
        JournalEntryCreate(
            entry_date="2026-06-30",
            source_type="manual_test",
            source_id="revenue-1",
            description="收入确认",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("10000.00"),
                    base_amount=Decimal("10000.00"),
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("10000.00"),
                    base_amount=Decimal("10000.00"),
                ),
            ],
        )
    )
    set_tax_accrual_rules(
        [
            TaxAccrualRule(
                tax_code="surcharge",
                tax_name="附加税",
                rate=Decimal("0.06"),
                base_account_codes=["6001"],
                debit_account_code="6403",
            )
        ]
    )

    results = generate_period_close_actions(
        account_set_id="default",
        period="2026-06",
        actions=["tax_accrual"],
        generated_by="finance-user",
    )

    assert results[0].status == "generated"
    assert results[0].amount == Decimal("600.00")
