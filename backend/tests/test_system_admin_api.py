from fastapi.testclient import TestClient

from app.main import app
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def test_system_admin_lists_permissions_roles_and_users_without_secrets():
    reset_system_admin_store()

    permissions_response = client.get("/api/v1/system/permissions")
    roles_response = client.get("/api/v1/system/roles")
    users_response = client.get("/api/v1/system/users")

    assert permissions_response.status_code == 200
    assert roles_response.status_code == 200
    assert users_response.status_code == 200

    permissions = permissions_response.json()["permissions"]
    permission_codes = {permission["code"] for permission in permissions}
    assert {
        "voucher.review",
        "ledger.read",
        "fixed_asset.read",
        "fixed_asset.depreciate",
        "fixed_asset_accounting.read",
        "fixed_asset_accounting.post",
        "fixed_asset_accounting.impair",
        "fixed_asset_accounting.dispose",
        "payroll.calculate",
        "payroll_accounting.read",
        "payroll_accounting.accrue",
        "payroll_accounting.pay",
        "payroll_accounting.remit",
        "statement.generate",
        "statement.validate",
        "statement.mapping.view",
        "statement.mapping.manage",
        "statement.snapshot.create",
        "statement.snapshot.lock",
        "statement.archive.view",
        "statement.export",
        "archive.read",
        "archive.document.create",
        "archive.case.create",
        "archive.package.download",
        "archive.verification.update",
        "receivable_payable.read",
        "receivable_payable.settle",
        "receivable_payable.bad_debt",
        "bank_reconciliation.read",
        "bank_reconciliation.import",
        "bank_reconciliation.match",
        "bank_reconciliation.confirm",
        "system.audit.read",
        "platform.client.manage",
    }.issubset(permission_codes)
    assert all(permission["module_id"] for permission in permissions)
    assert all(permission["risk_level"] in {"low", "medium", "high"} for permission in permissions)

    roles = roles_response.json()["roles"]
    role_by_id = {role["id"]: role for role in roles}
    assert "system.audit.read" in role_by_id["super_admin"]["permission_codes"]
    assert "voucher.review" in role_by_id["finance_manager"]["permission_codes"]
    assert "ledger.read" in role_by_id["finance_manager"]["permission_codes"]
    assert "fixed_asset.depreciate" in role_by_id["finance_manager"]["permission_codes"]
    assert "fixed_asset_accounting.post" in role_by_id["finance_manager"]["permission_codes"]
    assert "fixed_asset_accounting.impair" in role_by_id["finance_manager"]["permission_codes"]
    assert "fixed_asset_accounting.dispose" in role_by_id["finance_manager"]["permission_codes"]
    assert "payroll.calculate" in role_by_id["finance_manager"]["permission_codes"]
    assert "payroll_accounting.read" in role_by_id["finance_manager"]["permission_codes"]
    assert "payroll_accounting.accrue" in role_by_id["finance_manager"]["permission_codes"]
    assert "payroll_accounting.pay" in role_by_id["finance_manager"]["permission_codes"]
    assert "payroll_accounting.remit" in role_by_id["finance_manager"]["permission_codes"]
    assert "statement.generate" in role_by_id["finance_manager"]["permission_codes"]
    assert "statement.validate" in role_by_id["finance_manager"]["permission_codes"]
    assert "statement.mapping.view" in role_by_id["finance_manager"]["permission_codes"]
    assert "statement.mapping.manage" in role_by_id["finance_manager"]["permission_codes"]
    assert "statement.snapshot.create" in role_by_id["finance_manager"]["permission_codes"]
    assert "statement.snapshot.lock" in role_by_id["finance_manager"]["permission_codes"]
    assert "statement.archive.view" in role_by_id["finance_manager"]["permission_codes"]
    assert "statement.export" in role_by_id["finance_manager"]["permission_codes"]
    assert "archive.read" in role_by_id["finance_manager"]["permission_codes"]
    assert "archive.document.create" in role_by_id["finance_manager"]["permission_codes"]
    assert "archive.case.create" in role_by_id["finance_manager"]["permission_codes"]
    assert "archive.package.download" in role_by_id["finance_manager"]["permission_codes"]
    assert "archive.verification.update" in role_by_id["finance_manager"]["permission_codes"]
    assert "receivable_payable.read" in role_by_id["finance_manager"]["permission_codes"]
    assert "receivable_payable.settle" in role_by_id["finance_manager"]["permission_codes"]
    assert "receivable_payable.bad_debt" in role_by_id["finance_manager"]["permission_codes"]
    assert "bank_reconciliation.read" in role_by_id["finance_manager"]["permission_codes"]
    assert "bank_reconciliation.import" in role_by_id["finance_manager"]["permission_codes"]
    assert "bank_reconciliation.match" in role_by_id["finance_manager"]["permission_codes"]
    assert "bank_reconciliation.confirm" in role_by_id["finance_manager"]["permission_codes"]
    assert "ledger.read" in role_by_id["auditor"]["permission_codes"]
    assert "fixed_asset_accounting.read" in role_by_id["auditor"]["permission_codes"]
    assert "receivable_payable.read" in role_by_id["auditor"]["permission_codes"]
    assert "bank_reconciliation.read" in role_by_id["auditor"]["permission_codes"]
    assert "platform.client.manage" in role_by_id["api_integrator"]["permission_codes"]

    users = users_response.json()["users"]
    finance_manager = next(user for user in users if user["id"] == "u-finance-manager")
    assert finance_manager["active"] is True
    assert finance_manager["role_ids"] == ["finance_manager"]
    assert "password" not in finance_manager
    assert "token" not in finance_manager


def test_authorize_endpoint_returns_allow_and_deny_decisions():
    reset_system_admin_store()

    allow_response = client.post(
        "/api/v1/system/authorize",
        json={"user_id": "u-finance-manager", "permission_code": "voucher.review"},
    )
    deny_response = client.post(
        "/api/v1/system/authorize",
        json={"user_id": "u-api-integrator", "permission_code": "voucher.review"},
    )

    assert allow_response.status_code == 200
    assert allow_response.json()["allowed"] is True
    assert allow_response.json()["matched_role_ids"] == ["finance_manager"]

    assert deny_response.status_code == 200
    assert deny_response.json()["allowed"] is False
    assert "权限不足" in deny_response.json()["reason"]


def test_audit_log_can_be_recorded_and_filtered_by_module():
    reset_system_admin_store()

    create_response = client.post(
        "/api/v1/system/audit-logs",
        json={
            "actor_id": "u-finance-manager",
            "module_id": "finance-center",
            "event": "voucher.review",
            "target_id": "voucher-202606-0001",
            "result": "success",
            "metadata": {"voucher_number": "记-202606-0001"},
        },
    )

    assert create_response.status_code == 200
    log = create_response.json()
    assert log["id"].startswith("audit-")
    assert log["actor_id"] == "u-finance-manager"
    assert log["module_id"] == "finance-center"
    assert log["event"] == "voucher.review"
    assert log["result"] == "success"
    assert log["metadata"]["voucher_number"] == "记-202606-0001"

    list_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    assert list_response.status_code == 200
    logs = list_response.json()["logs"]
    assert any(item["id"] == log["id"] for item in logs)
    assert all(item["module_id"] == "finance-center" for item in logs)


def test_audit_log_rejects_extra_fields_and_invalid_result():
    reset_system_admin_store()

    response = client.post(
        "/api/v1/system/audit-logs",
        json={
            "actor_id": "u-finance-manager",
            "module_id": "finance-center",
            "event": "voucher.review",
            "target_id": "voucher-202606-0001",
            "result": "done",
            "metadata": {},
            "forged": True,
        },
    )

    assert response.status_code == 422
