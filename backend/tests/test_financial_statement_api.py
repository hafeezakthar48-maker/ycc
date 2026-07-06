import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_statement_api(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    monkeypatch.setenv("FINANCE_AI_ACCOUNTING_DB_PATH", str(tmp_path / "formal-accounting.sqlite3"))
    reset_voucher_store()
    reset_accounting_store()
    reset_system_admin_store()


def test_financial_statement_api_generates_bundle_and_records_success_audit():
    response = client.post(
        "/api/v1/financial-statements/generate",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"period": "2026-06", "account_set_id": "default", "operator": "财务主管"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2026-06"
    assert payload["balance_sheet"]["title"] == "资产负债表"
    assert payload["income_statement"]["title"] == "利润表"
    assert payload["cash_flow_statement"]["title"] == "现金流量表"
    assert payload["equity_statement"]["title"] == "所有者权益变动表"

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    log = logs_response.json()["logs"][0]
    assert log["event"] == "statement.generate"
    assert log["actor_id"] == "u-finance-manager"
    assert log["result"] == "success"
    assert log["metadata"]["period"] == "2026-06"
    assert log["metadata"]["statement_count"] == 5


def test_financial_statement_api_rejects_unauthorized_actor_and_records_denied_audit():
    response = client.post(
        "/api/v1/financial-statements/generate",
        headers={"X-Actor-Id": "u-api-integrator"},
        json={"period": "2026-06"},
    )

    assert response.status_code == 403

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    log = logs_response.json()["logs"][0]
    assert log["event"] == "statement.generate"
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "statement.generate"


def test_finance_center_registry_declares_financial_statement_api():
    response = client.get("/api/v1/modules/finance-center")

    assert response.status_code == 200
    module = response.json()
    assert "/api/v1/financial-statements" in module["api_prefixes"]
    assert "statement.generate" in module["audit_events"]
