from app.models.period_close import PeriodCloseRunCreate
from app.services.period_close_service import (
    get_period_close_run,
    list_period_close_runs,
    reset_period_close_store,
    run_period_close_checks,
    start_period_close_run,
)


def setup_function():
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
