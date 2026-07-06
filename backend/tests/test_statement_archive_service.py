from app.models.financial_statement import FinancialStatementGenerateRequest
from app.services.financial_statement_service import generate_financial_statements
from app.services.statement_archive_service import (
    create_statement_snapshot,
    get_statement_snapshot,
    list_statement_snapshots,
    lock_statement_snapshot,
    record_statement_export,
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


def test_lock_statement_snapshot_marks_archived_when_formal_source():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))
    snapshot = create_statement_snapshot(bundle=bundle, created_by="finance-user")

    locked = lock_statement_snapshot(snapshot.snapshot_id, locked_by="finance-manager")

    assert locked.locked is True
    assert locked.locked_by == "finance-manager"
    assert locked.archive_status in {"archived", "demo_only"}


def test_record_statement_export_keeps_snapshot_reference():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))
    snapshot = create_statement_snapshot(bundle=bundle, created_by="finance-user")

    export = record_statement_export(
        snapshot_id=snapshot.snapshot_id,
        export_format="xlsx",
        filename="financial-statements-default-2026-06-v1.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        exported_by="finance-user",
    )

    assert export.snapshot_id == snapshot.snapshot_id
    assert export.export_format == "xlsx"
    assert export.filename.endswith(".xlsx")
