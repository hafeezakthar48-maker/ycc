from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()


def test_get_accounting_accounts_requires_accounting_permission():
    response = client.get("/api/v1/accounting/accounts?account_set_id=default", headers={"X-Actor-Id": "u-auditor"})

    assert response.status_code == 403


def test_finance_manager_can_read_accounting_accounts():
    response = client.get("/api/v1/accounting/accounts?account_set_id=default", headers={"X-Actor-Id": "u-finance-manager"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["account_set_id"] == "default"
    assert any(account["account_code"] == "1001" for account in payload["accounts"])


def test_finance_center_registry_includes_accounting_api():
    response = client.get("/api/v1/modules/finance-center")

    assert response.status_code == 200
    module = response.json()
    assert "/api/v1/accounting" in module["api_prefixes"]
    assert "accounting.entry.post" in module["audit_events"]
