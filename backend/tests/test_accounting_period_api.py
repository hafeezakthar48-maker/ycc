from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    reset_voucher_store()
    reset_system_admin_store()
    reset_accounting_period_store()


def test_accounting_period_api_lists_account_sets_and_periods():
    headers = {"X-Actor-Id": "u-finance-manager"}

    account_sets_response = client.get("/api/v1/ledger/account-sets", headers=headers)
    periods_response = client.get("/api/v1/ledger/periods?account_set_id=default", headers=headers)

    assert account_sets_response.status_code == 200
    assert account_sets_response.json()["account_sets"][0]["id"] == "default"
    assert account_sets_response.json()["account_sets"][0]["is_default"] is True

    assert periods_response.status_code == 200
    periods = periods_response.json()["periods"]
    assert any(period["period"] == "2026-06" and period["status"] == "open" for period in periods)


def test_accounting_period_close_and_reopen_record_audit_logs():
    headers = {"X-Actor-Id": "u-finance-manager"}

    close_response = client.post(
        "/api/v1/ledger/periods/2026-06/close",
        json={"operator": "财务主管"},
        headers=headers,
    )
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"

    reopen_response = client.post(
        "/api/v1/ledger/periods/2026-06/reopen",
        json={"operator": "财务主管"},
        headers=headers,
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["status"] == "open"

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=10")
    assert logs_response.status_code == 200
    events = [log["event"] for log in logs_response.json()["logs"]]
    assert "ledger.period.close" in events
    assert "ledger.period.reopen" in events


def test_accounting_period_manage_rejects_unauthorized_actor():
    response = client.post(
        "/api/v1/ledger/periods/2026-06/close",
        json={"operator": "接口集成员"},
        headers={"X-Actor-Id": "u-api-integrator"},
    )

    assert response.status_code == 403
    assert "权限不足" in response.json()["detail"]

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    log = logs_response.json()["logs"][0]
    assert log["event"] == "ledger.period.close"
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "ledger.period.manage"


def test_finance_manager_has_accounting_period_manage_permission():
    response = client.post(
        "/api/v1/system/authorize",
        json={"user_id": "u-finance-manager", "permission_code": "ledger.period.manage"},
    )

    assert response.status_code == 200
    assert response.json()["allowed"] is True
