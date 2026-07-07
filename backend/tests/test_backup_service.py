from decimal import Decimal

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_archive_service import reset_accounting_archive_store
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import post_journal_entry, reset_accounting_store
from app.services.backup_service import (
    build_accounting_backup_package,
    create_accounting_backup_manifest,
    get_latest_backup_manifest,
    rehearse_accounting_restore,
    reset_backup_store,
)
from app.services.statement_mapping_service import reset_statement_mapping_store
from app.services.system_admin_service import reset_system_admin_store


def setup_function():
    reset_accounting_store()
    reset_accounting_archive_store()
    reset_accounting_period_store()
    reset_statement_mapping_store()
    reset_system_admin_store()
    reset_backup_store()


def test_backup_manifest_lists_core_accounting_datasets_with_counts_and_checksums():
    post_journal_entry(_balanced_entry())

    manifest = create_accounting_backup_manifest("default", "2026-06", "backup-user")

    assert manifest.account_set_id == "default"
    assert manifest.period == "2026-06"
    assert manifest.actor_id == "backup-user"
    assert manifest.backup_manifest_id.startswith("backup-default-2026-06-")
    assert "journal_entries" in manifest.datasets
    assert "journal_lines" in manifest.datasets
    assert "audit_logs" in manifest.datasets
    assert manifest.dataset_row_counts["journal_entries"] == 1
    assert manifest.dataset_row_counts["journal_lines"] == 2
    assert manifest.dataset_checksums["journal_entries"]
    assert get_latest_backup_manifest("default", "2026-06").backup_manifest_id == manifest.backup_manifest_id


def test_restore_rehearsal_records_row_counts_and_integrity_status():
    post_journal_entry(_balanced_entry())
    manifest = create_accounting_backup_manifest("default", "2026-06", "backup-user")

    rehearsal = rehearse_accounting_restore(
        backup_manifest_id=manifest.backup_manifest_id,
        target_database_path="D:/tmp/formal-accounting-restore.sqlite3",
        actor_id="restore-user",
    )

    assert rehearsal.status == "passed"
    assert rehearsal.backup_manifest_id == manifest.backup_manifest_id
    assert rehearsal.target_database_path == "D:/tmp/formal-accounting-restore.sqlite3"
    assert rehearsal.row_counts["journal_entries"] == 1
    assert rehearsal.integrity_status == "warning"
    assert rehearsal.completed_at >= rehearsal.started_at


def test_backup_package_exports_manifest_as_zip_payload():
    manifest = create_accounting_backup_manifest("default", "2026-06", "backup-user")

    package = build_accounting_backup_package(manifest.backup_manifest_id)

    assert package.backup_manifest_id == manifest.backup_manifest_id
    assert package.filename.endswith(".zip")
    assert package.content_type == "application/zip"
    assert package.content.startswith(b"PK")
    assert package.size == len(package.content)


def _balanced_entry():
    return JournalEntryCreate(
        account_set_id="default",
        entry_date="2026-06-18",
        source_type="manual",
        source_id="backup-entry-1",
        description="备份测试正式分录",
        created_by="财务主管",
        posted_by="财务主管",
        lines=[
            JournalLineCreate(
                account_code="6602",
                account_name="管理费用",
                direction="debit",
                original_amount=Decimal("100.00"),
                base_amount=Decimal("100.00"),
                description="费用",
            ),
            JournalLineCreate(
                account_code="2202",
                account_name="应付账款",
                direction="credit",
                original_amount=Decimal("100.00"),
                base_amount=Decimal("100.00"),
                description="应付",
            ),
        ],
    )
