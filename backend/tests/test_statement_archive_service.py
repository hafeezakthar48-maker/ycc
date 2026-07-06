from app.models.financial_statement import FinancialStatementGenerateRequest
from app.services.financial_statement_service import generate_financial_statements
from app.services.statement_archive_service import (
    create_statement_snapshot,
    get_statement_snapshot,
    list_statement_snapshots,
    reset_statement_archive_store,
)


def setup_function():
    reset_statement_archive_store()


def test_create_statement_snapshot_assigns_version_and_hash():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))

    first = create_statement_snapshot(bundle=bundle, created_by="finance-user")
    second = create_statement_snapshot(bundle=bundle, created_by="finance-user")
    loaded = get_statement_snapshot(first.snapshot_id)
    listed = list_statement_snapshots(account_set_id="default", period="2026-06")

    assert first.version == 1
    assert second.version == 2
    assert first.content_hash == second.content_hash
    assert loaded.snapshot_id == first.snapshot_id
    assert listed.total == 2
    assert listed.items[0].version == 2
