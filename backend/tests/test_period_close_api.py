from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import reset_accounting_store
from app.services.fixed_asset_service import reset_fixed_asset_store
from app.services.payroll_service import reset_payroll_store
from app.services.period_close_service import reset_period_close_store
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


def setup_function():
    reset_accounting_period_store()
    reset_accounting_store()
    reset_fixed_asset_store()
    reset_payroll_store()
    reset_period_close_store()
    reset_system_admin_store()
    reset_voucher_store()


def test_period_close_checks_endpoint_returns_items_and_audit_log():
    response = client.post(
        "/api/v1/period-close/checks",
        json={"account_set_id": "default", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["items"]

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&event=period_close.checks_completed")
    assert logs_response.status_code == 200
    assert len(logs_response.json()["logs"]) == 1


def test_period_close_generate_endpoint_returns_action_results():
    response = client.post(
        "/api/v1/period-close/actions/generate",
        json={
            "account_set_id": "default",
            "period": "2026-06",
            "actions": ["profit_loss_carryforward"],
            "generated_by": "finance-user",
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["action_type"] == "profit_loss_carryforward"


def test_period_close_close_and_reopen_endpoints_record_audit_events():
    close_response = client.post(
        "/api/v1/period-close/close",
        json={"account_set_id": "default", "period": "2026-06", "operator": "finance-user"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    reopen_response = client.post(
        "/api/v1/period-close/reopen",
        json={"account_set_id": "default", "period": "2026-06", "operator": "finance-user"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"
    assert reopen_response.status_code == 200
    assert reopen_response.json()["status"] == "open"

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=10")
    events = {item["event"] for item in logs_response.json()["logs"]}
    assert {"period_close.period_closed", "period_close.period_reopened"}.issubset(events)


def test_period_close_module_and_permissions_are_registered():
    module_response = client.get("/api/v1/modules/finance-center")
    permissions_response = client.get("/api/v1/system/permissions")

    assert module_response.status_code == 200
    assert "/api/v1/period-close" in module_response.json()["api_prefixes"]

    permission_codes = {item["code"] for item in permissions_response.json()["permissions"]}
    assert {"period_close.view", "period_close.generate", "period_close.close", "period_close.reopen"}.issubset(permission_codes)
