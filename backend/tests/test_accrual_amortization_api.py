from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import reset_accounting_store
from app.services.accrual_amortization_service import reset_accrual_amortization_store
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()
    reset_accrual_amortization_store()
    reset_system_admin_store()


def teardown_function():
    reset_accounting_period_store()


def test_accrual_amortization_api_runs_schedule_and_loan_interest_workflow():
    create_response = client.post(
        "/api/v1/accrual-amortization/schedules",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "schedule_code": "AMORT-2026-001",
            "schedule_type": "prepaid_amortization",
            "start_period": "2026-06",
            "end_period": "2026-08",
            "total_amount": "3000.00",
            "debit_account_code": "6602",
            "credit_account_code": "1801",
        },
    )
    list_response = client.get(
        "/api/v1/accrual-amortization/schedules",
        params={"account_set_id": "default"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    post_response = client.post(
        "/api/v1/accrual-amortization/schedules/AMORT-2026-001/post",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "period": "2026-06"},
    )
    interest_response = client.post(
        "/api/v1/accrual-amortization/loan-interest",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "loan_code": "LOAN-2026-001",
            "period": "2026-06",
            "principal": "1000000.00",
            "annual_rate": "0.036",
            "start_period": "2026-06",
            "end_period": "2026-12",
        },
    )

    assert create_response.status_code == 200
    assert create_response.json()["schedule_code"] == "AMORT-2026-001"
    assert list_response.status_code == 200
    assert list_response.json()["total_schedules"] == 1
    assert post_response.status_code == 200
    assert post_response.json()["source_id"] == "schedule_posting:default:2026-06:AMORT-2026-001"
    assert interest_response.status_code == 200
    assert interest_response.json()["source_id"] == "loan_interest_accrual:default:2026-06:LOAN-2026-001"

    audit_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=20")
    events = [log["event"] for log in audit_response.json()["logs"]]
    assert "accrual_amortization.schedule.create" in events
    assert "accrual_amortization.schedule.read" in events
    assert "accrual_amortization.schedule.post" in events
    assert "accrual_amortization.loan_interest.post" in events


def test_accrual_amortization_api_rejects_unauthorized_post_and_records_audit():
    response = client.post(
        "/api/v1/accrual-amortization/schedules",
        headers={"X-Actor-Id": "u-auditor"},
        json={
            "account_set_id": "default",
            "schedule_code": "AMORT-2026-001",
            "schedule_type": "prepaid_amortization",
            "start_period": "2026-06",
            "end_period": "2026-08",
            "total_amount": "3000.00",
            "debit_account_code": "6602",
            "credit_account_code": "1801",
        },
    )

    assert response.status_code == 403
    audit_response = client.get(
        "/api/v1/system/audit-logs",
        params={"event": "accrual_amortization.schedule.create", "actor_id": "u-auditor"},
    )
    log = audit_response.json()["logs"][0]
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "accrual_amortization.write"
