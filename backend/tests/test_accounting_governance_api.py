from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_archive_service import reset_accounting_archive_store
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import reset_accounting_store
from app.services.backup_service import reset_backup_store
from app.services.statement_mapping_service import reset_statement_mapping_store
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


def setup_function():
    reset_voucher_store()
    reset_accounting_store()
    reset_accounting_period_store()
    reset_accounting_archive_store()
    reset_statement_mapping_store()
    reset_backup_store()
    reset_system_admin_store()


def test_accounting_governance_api_runs_go_live_workflow_and_audits():
    headers = {"X-Actor-Id": "u-finance-manager"}

    integrity = client.get(
        "/api/v1/accounting-governance/integrity-checks?account_set_id=default&period=2026-06",
        headers=headers,
    )
    assert integrity.status_code == 200
    assert integrity.json()["overall_status"] == "pass"

    preview = client.post(
        "/api/v1/accounting-governance/migration-preview",
        json={"account_set_id": "default", "period": "2026-06"},
        headers=headers,
    )
    assert preview.status_code == 200
    assert preview.json()["mode"] == "dry_run"

    backup = client.post(
        "/api/v1/accounting-governance/backups",
        json={"account_set_id": "default", "period": "2026-06", "actor_id": "backup-user"},
        headers=headers,
    )
    assert backup.status_code == 200
    backup_manifest_id = backup.json()["backup_manifest_id"]

    restore = client.post(
        "/api/v1/accounting-governance/restore-rehearsals",
        json={
            "backup_manifest_id": backup_manifest_id,
            "target_database_path": "D:/tmp/formal-accounting-restore.sqlite3",
            "actor_id": "restore-user",
        },
        headers=headers,
    )
    assert restore.status_code == 200
    assert restore.json()["status"] == "passed"

    matrix = client.get("/api/v1/accounting-governance/permission-matrix", headers=headers)
    assert matrix.status_code == 200
    assert "accounting_migration.apply" in matrix.json()["required_permissions"]

    gate = client.get(
        "/api/v1/accounting-governance/go-live-gate"
        "?account_set_id=default&period=2026-06"
        "&backend_tests=passed&frontend_tests=passed&frontend_build=passed",
        headers=headers,
    )
    assert gate.status_code == 200
    assert gate.json()["status"] == "pass"

    logs = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=20").json()["logs"]
    events = {log["event"] for log in logs}
    assert "accounting_governance.integrity.read" in events
    assert "accounting_governance.migration.preview" in events
    assert "accounting_governance.backup.create" in events
    assert "accounting_governance.restore.rehearsal" in events
    assert "accounting_governance.go_live_gate.read" in events


def test_accounting_governance_api_rejects_backup_without_permission():
    response = client.post(
        "/api/v1/accounting-governance/backups",
        json={"account_set_id": "default", "period": "2026-06", "actor_id": "backup-user"},
        headers={"X-Actor-Id": "u-auditor"},
    )

    assert response.status_code == 403
