from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store
from app.services.receivable_payable_service import reset_receivable_payable_store
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()
    reset_receivable_payable_store()
    reset_system_admin_store()


def test_receivable_balance_endpoint_requires_permission_and_returns_shape():
    response = client.get(
        "/api/v1/receivable-payable/balances?account_set_id=default&period=2026-06&open_item_type=receivable",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["open_item_type"] == "receivable"
    assert "total_base_balance" in response.json()


def test_receivable_aging_endpoint_returns_buckets():
    response = client.get(
        "/api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert [bucket["bucket_code"] for bucket in response.json()["buckets"]] == [
        "0-30",
        "31-60",
        "61-90",
        "91-180",
        "181-365",
        "365+",
    ]


def test_receivable_payable_rejects_user_without_permission_and_records_denied_audit():
    response = client.get(
        "/api/v1/receivable-payable/balances?account_set_id=default&period=2026-06&open_item_type=receivable",
        headers={"X-Actor-Id": "u-api-integrator"},
    )

    assert response.status_code == 403
    audit_response = client.get("/api/v1/system/audit-logs?event=receivable_payable.balance.read&actor_id=u-api-integrator")
    assert audit_response.status_code == 200
    logs = audit_response.json()["logs"]
    assert logs[0]["result"] == "denied"
    assert logs[0]["metadata"]["permission_code"] == "receivable_payable.read"
