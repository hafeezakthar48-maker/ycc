from app.services.accounting_archive_service import reset_accounting_archive_store
from app.services.accounting_governance_service import (
    build_formal_accounting_permission_matrix,
    evaluate_formal_accounting_go_live_gate,
)
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import reset_accounting_store
from app.services.backup_service import create_accounting_backup_manifest, rehearse_accounting_restore, reset_backup_store
from app.services.statement_mapping_service import reset_statement_mapping_store
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


REGRESSION_RESULTS = {
    "backend_tests": "passed",
    "frontend_tests": "passed",
    "frontend_build": "passed",
}


def setup_function():
    reset_voucher_store()
    reset_accounting_store()
    reset_accounting_period_store()
    reset_accounting_archive_store()
    reset_statement_mapping_store()
    reset_backup_store()
    reset_system_admin_store()


def test_permission_matrix_includes_segregation_of_duties():
    matrix = build_formal_accounting_permission_matrix()

    assert "voucher.post" in matrix.required_permissions
    assert "period_close.close" in matrix.required_permissions
    assert "accounting_migration.apply" in matrix.required_permissions
    assert "accounting_backup.create" in matrix.required_permissions
    assert matrix.missing_permissions == []
    assert "finance_manager" in matrix.role_coverage["accounting_migration.apply"]
    assert matrix.segregation_rules


def test_go_live_gate_blocks_without_backup_restore_rehearsal():
    gate = evaluate_formal_accounting_go_live_gate(
        account_set_id="default",
        period="2026-06",
        regression_results=REGRESSION_RESULTS,
    )

    assert gate.status == "blocked"
    assert "backup_restore_rehearsal" in gate.blockers


def test_go_live_gate_passes_after_backup_restore_and_regression_results():
    manifest = create_accounting_backup_manifest("default", "2026-06", "backup-user")
    rehearse_accounting_restore(
        backup_manifest_id=manifest.backup_manifest_id,
        target_database_path="D:/tmp/formal-accounting-restore.sqlite3",
        actor_id="restore-user",
    )

    gate = evaluate_formal_accounting_go_live_gate(
        account_set_id="default",
        period="2026-06",
        regression_results=REGRESSION_RESULTS,
    )

    assert gate.status == "pass"
    checks_by_code = {check.gate_code: check for check in gate.checks}
    assert checks_by_code["integrity_checks"].status == "pass"
    assert checks_by_code["migration_dry_run"].status == "pass"
    assert checks_by_code["backup_restore_rehearsal"].status == "pass"
    assert checks_by_code["permission_matrix"].status == "pass"
    assert checks_by_code["regression_commands"].status == "pass"
