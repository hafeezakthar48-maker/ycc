from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store
from app.services.bank_reconciliation_service import reset_bank_reconciliation_store
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()
    reset_bank_reconciliation_store()
    reset_system_admin_store()


def test_bank_statement_import_and_reconciliation_statement_endpoint():
    import_response = client.post(
        "/api/v1/bank-reconciliation/statements/import",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "lines": [
                {
                    "account_set_id": "default",
                    "bank_account_id": "bank-001",
                    "transaction_date": "2026-06-30",
                    "direction": "inflow",
                    "amount": "1200.00",
                    "currency": "CNY",
                    "counterparty_name": "上海客户A",
                    "summary": "销售回款",
                    "bank_reference": "B20260630001",
                }
            ],
        },
    )

    assert import_response.status_code == 200
    assert import_response.json()["imported_count"] == 1

    statement_response = client.get(
        "/api/v1/bank-reconciliation/statements",
        params={"account_set_id": "default", "bank_account_id": "bank-001", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert statement_response.status_code == 200
    assert statement_response.json()["bank_balance"] == "1200.00"
    assert "adjusted_bank_balance" in statement_response.json()


def test_bank_reconciliation_rejects_user_without_permission_and_records_denied_audit():
    response = client.get(
        "/api/v1/bank-reconciliation/statements",
        params={"account_set_id": "default", "bank_account_id": "bank-001", "period": "2026-06"},
        headers={"X-Actor-Id": "u-api-integrator"},
    )

    assert response.status_code == 403
    audit_response = client.get("/api/v1/system/audit-logs?event=bank_reconciliation.statement.read&actor_id=u-api-integrator")
    assert audit_response.status_code == 200
    logs = audit_response.json()["logs"]
    assert logs[0]["result"] == "denied"
    assert logs[0]["metadata"]["permission_code"] == "bank_reconciliation.read"
