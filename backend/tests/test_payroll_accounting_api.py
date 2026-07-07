from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import reset_accounting_store
from app.services.payroll_service import reset_payroll_store
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()
    reset_payroll_store()
    reset_system_admin_store()


def test_payroll_accounting_api_runs_formal_workflow_and_reads_batches():
    calculate_response = client.post(
        "/api/v1/payroll/calculate",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "period": "2026-06",
            "operator": "财务主管",
            "employees": [
                {
                    "employee_id": "E001",
                    "employee_name": "张会计",
                    "department": "财务部",
                    "base_salary": "10000.00",
                    "social_security_base": "10000.00",
                    "housing_fund_base": "10000.00",
                }
            ],
        },
    )
    batches_response = client.get(
        "/api/v1/payroll-accounting/batches",
        params={"account_set_id": "default", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    accrual_response = client.post(
        "/api/v1/payroll-accounting/accruals",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "period": "2026-06", "payroll_batch_id": "PAY-2026-06"},
    )
    payment_response = client.post(
        "/api/v1/payroll-accounting/payments",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "period": "2026-06",
            "payroll_batch_id": "PAY-2026-06",
            "bank_account_code": "1002",
        },
    )
    liability_response = client.post(
        "/api/v1/payroll-accounting/liability-payments",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "period": "2026-07",
            "payroll_batch_id": "PAY-2026-06",
            "bank_account_code": "1002",
        },
    )
    updated_batches_response = client.get(
        "/api/v1/payroll-accounting/batches",
        params={"account_set_id": "default", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert calculate_response.status_code == 200
    assert batches_response.status_code == 200
    assert batches_response.json()["batches"][0]["status"] == "calculated"
    assert accrual_response.status_code == 200
    assert accrual_response.json()["source_type"] == "payroll_accrual"
    assert payment_response.status_code == 200
    assert payment_response.json()["source_type"] == "payroll_payment"
    assert liability_response.status_code == 200
    assert liability_response.json()["source_type"] == "payroll_liability_payment"

    updated_batch = updated_batches_response.json()["batches"][0]
    assert updated_batch["status"] == "paid"
    assert updated_batch["accrual_journal_entry_id"].startswith("je-")
    assert updated_batch["payment_journal_entry_id"].startswith("je-")
    assert updated_batch["liability_payment_status"] == "remitted"
    assert updated_batch["liability_payment_journal_entry_id"].startswith("je-")

    audit_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=10")
    events = [log["event"] for log in audit_response.json()["logs"]]
    assert "payroll_accounting.batch.read" in events
    assert "payroll_accounting.accrual.post" in events
    assert "payroll_accounting.payment.post" in events
    assert "payroll_accounting.liability_payment.post" in events


def test_payroll_accounting_api_rejects_unauthorized_accrual_and_records_audit():
    response = client.post(
        "/api/v1/payroll-accounting/accruals",
        headers={"X-Actor-Id": "u-auditor"},
        json={"account_set_id": "default", "period": "2026-06", "payroll_batch_id": "PAY-2026-06"},
    )

    assert response.status_code == 403
    audit_response = client.get(
        "/api/v1/system/audit-logs",
        params={"event": "payroll_accounting.accrual.post", "actor_id": "u-auditor"},
    )
    log = audit_response.json()["logs"][0]
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "payroll_accounting.accrue"
