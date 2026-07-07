from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import reset_accounting_store
from app.services.inventory_accounting_service import reset_inventory_accounting_store
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()
    reset_inventory_accounting_store()
    reset_system_admin_store()


def teardown_function():
    reset_accounting_period_store()


def test_inventory_accounting_api_runs_inventory_workflow_and_reads_balances():
    receipt_response = client.post(
        "/api/v1/inventory-accounting/purchase-receipts",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "sku_id": "SKU-001",
            "warehouse_id": "WH-SH",
            "period": "2026-06",
            "quantity": "10",
            "amount": "1000.00",
            "supplier_id": "SUP-001",
        },
    )
    balances_response = client.get(
        "/api/v1/inventory-accounting/balances",
        params={"account_set_id": "default"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    issue_response = client.post(
        "/api/v1/inventory-accounting/sales-issues",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "sku_id": "SKU-001",
            "warehouse_id": "WH-SH",
            "period": "2026-06",
            "quantity": "3",
        },
    )
    impairment_response = client.post(
        "/api/v1/inventory-accounting/impairments",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "sku_id": "SKU-001",
            "period": "2026-06",
            "amount": "500.00",
        },
    )
    count_response = client.post(
        "/api/v1/inventory-accounting/count-variances",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "sku_id": "SKU-001",
            "warehouse_id": "WH-SH",
            "period": "2026-06",
            "actual_quantity": "6",
            "approved_by": "controller",
            "approved_at": "2026-06-30T10:00:00Z",
        },
    )

    assert receipt_response.status_code == 200
    assert receipt_response.json()["source_id"] == "inventory_receipt:default:2026-06:SKU-001:SUP-001"
    assert balances_response.status_code == 200
    assert balances_response.json()["balances"][0]["moving_average_cost"] == "100.00"
    assert balances_response.json()["movements"][0]["movement_type"] == "purchase_receipt"
    assert issue_response.status_code == 200
    assert issue_response.json()["cogs_account_code"] == "6401"
    assert impairment_response.status_code == 200
    assert impairment_response.json()["source_type"] == "inventory_impairment"
    assert count_response.status_code == 200
    assert count_response.json()["variance_type"] == "loss"

    audit_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=20")
    events = [log["event"] for log in audit_response.json()["logs"]]
    assert "inventory_accounting.balance.read" in events
    assert "inventory_accounting.receipt.post" in events
    assert "inventory_accounting.sales_issue.post" in events
    assert "inventory_accounting.impairment.post" in events
    assert "inventory_accounting.count_variance.post" in events


def test_inventory_accounting_api_rejects_unauthorized_receipt_and_records_audit():
    response = client.post(
        "/api/v1/inventory-accounting/purchase-receipts",
        headers={"X-Actor-Id": "u-auditor"},
        json={
            "account_set_id": "default",
            "sku_id": "SKU-001",
            "warehouse_id": "WH-SH",
            "period": "2026-06",
            "quantity": "10",
            "amount": "1000.00",
            "supplier_id": "SUP-001",
        },
    )

    assert response.status_code == 403
    audit_response = client.get(
        "/api/v1/system/audit-logs",
        params={"event": "inventory_accounting.receipt.post", "actor_id": "u-auditor"},
    )
    log = audit_response.json()["logs"][0]
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "inventory_accounting.receipt"
